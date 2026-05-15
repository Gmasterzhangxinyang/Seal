"""
WeArm 机械臂 2D 侧视图仿真可视化

无需连接实物，基于 kinematics.py 参数在 matplotlib 里画出：
  - 各连杆姿态
  - 末端印章朝向
  - 盖章下压轨迹
  - 关节角度标注

用法:
    python -m simulation.visualize              # 默认盖章位置
    python -m simulation.visualize --x 120 --y 0 --z 30   # 指定坐标
    python -m simulation.visualize --animate    # 动画演示盖章过程

前提: matplotlib 已安装 (pip install matplotlib)
"""

import math
import argparse
import sys
import os

# 把 backend 目录加到 path，方便导入 kinematics
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, "apps", "backend"))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
import numpy as np

from hardware.kinematics import (
    H0, L1, L2, L3,
    inverse_kinematics,
    pwm_to_deg,
    deg_to_pwm,
)

# ─── 正向运动学（用于绘图） ────────────────────────────────────────────────


def forward_kinematics(joint_angles_deg: dict) -> list[tuple[float, float]]:
    """
    给定关节角度 (度)，计算各关节点在 YZ 平面内的坐标。

    返回: [(y0,z0), (y1,z1), (y2,z2), (y3,z3), (y_end,z_end)]
          0=底座旋转轴, 1=肩, 2=肘, 3=腕, end=末端(印章)
    """
    θ1 = math.radians(joint_angles_deg[1])  # 大臂相对水平面的角度
    θ2 = math.radians(joint_angles_deg[2])  # 小臂弯曲角
    θ3 = math.radians(joint_angles_deg[3])  # 手腕角

    # 坐标系: Y 水平, Z 垂直向上
    p0 = (0.0, 0.0)  # 底座旋转轴
    p1 = (0.0, H0)  # 肩关节
    p2 = (p1[0] + L1 * math.cos(θ1), p1[1] + L1 * math.sin(θ1))  # 肘
    p3 = (p2[0] + L2 * math.cos(θ1 + θ2), p2[1] + L2 * math.sin(θ1 + θ2))  # 腕
    pend = (p3[0] + L3 * math.cos(θ1 + θ2 + θ3), p3[1] + L3 * math.sin(θ1 + θ2 + θ3))

    return [p0, p1, p2, p3, pend]


def draw_arm(ax, joints, stamp_angle_deg=None, color="steelblue", alpha=1.0, label=""):
    """在给定 axes 上画出机械臂。joints 是 5 个点的列表 [(y,z),...]"""
    ys = [p[0] for p in joints]
    zs = [p[1] for p in joints]

    # 连杆
    ax.plot(ys, zs, "-o", color=color, linewidth=3, markersize=6, alpha=alpha, label=label)

    # 关节标注
    labels = ["底座", "肩", "肘", "腕", "印章"]
    for i, (y, z) in enumerate(joints):
        ax.annotate(
            labels[i],
            (y, z),
            textcoords="offset points",
            xytext=(8, 6),
            fontsize=8,
            color=color,
            alpha=alpha,
        )

    # 在末端画印章朝向指示
    if stamp_angle_deg is not None:
        end = joints[-1]
        direction_rad = math.radians(stamp_angle_deg)
        stamp_len = L3 * 0.6
        ax.annotate(
            "",
            xy=(end[0] + stamp_len * math.cos(direction_rad),
                end[1] + stamp_len * math.sin(direction_rad)),
            xytext=end,
            arrowprops=dict(arrowstyle="->", color="red", lw=2, alpha=alpha),
        )
        # 画印章水平面（小横线）
        perp = direction_rad + math.pi / 2
        half = L3 * 0.3
        ax.plot(
            [end[0] + half * math.cos(perp), end[0] - half * math.cos(perp)],
            [end[1] + half * math.sin(perp), end[1] - half * math.sin(perp)],
            color="red", linewidth=3, alpha=alpha,
        )


def compute_all_joint_info(ik_result: dict | None):
    """从 IK 结果提取所有关节角度（度）"""
    if ik_result is None:
        return None
    angles = {}
    for sid in [0, 1, 2, 3]:
        angles[sid] = pwm_to_deg(ik_result[sid])
    return angles


# ─── 绘制盖章轨迹 ──────────────────────────────────────────────────────────


def plot_stamp_trajectory(
    x: float, y: float, z: float,
    wrist_angle: float = -90.0,
    lift_height: float = 40.0,
    save_path: str | None = None,
):
    """绘制机械臂在盖章轨迹上的多个姿态"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Y (水平), mm")
    ax.set_ylabel("Z (垂直), mm")

    # 底座
    ax.add_patch(mpatches.Rectangle((-25, -10), 50, 10, color="gray", alpha=0.3))

    # 工作面
    ax.axhline(y=0, color="saddlebrown", linestyle="--", alpha=0.5, linewidth=1)
    ax.annotate("工作面", (10, 2), fontsize=9, color="saddlebrown", alpha=0.7)

    # 计算轨迹上的关键帧
    # 1) 起始位（抬起）→ 2) 接近位 → 3) 接触位 → 4) 下压位
    keyframes = [
        (z + lift_height, "起始 (抬起)"),
        (z + lift_height * 0.4, "接近"),
        (z, "接触"),
        (z, "下压"),
    ]

    colors = ["lightblue", "skyblue", "steelblue", "darkblue"]

    for (z_kf, label), color in zip(keyframes, colors):
        ik = inverse_kinematics(x, y, z_kf, wrist_angle=wrist_angle)
        if ik is None:
            print(f"  ⚠ {label}: IK 无解 (z={z_kf:.1f})")
            continue
        angles = compute_all_joint_info(ik)
        joints = forward_kinematics(angles)
        draw_arm(ax, joints, stamp_angle_deg=wrist_angle, color=color, label=label)
        print(f"  {label}: θ=({angles[0]:.0f}°,{angles[1]:.0f}°,{angles[2]:.0f}°,{angles[3]:.0f}°) "
              f"→ 末端 Y={joints[-1][0]:.1f} Z={joints[-1][1]:.1f}")

    # 画目标十字
    ax.plot(y, z, "rx", markersize=12, markeredgewidth=2, label="盖章目标")

    # 工作空间弧线
    theta_range = np.linspace(-math.pi / 2, math.pi / 2, 100)
    workspace_r = np.array([L1 + L2 + L3, L1 + L2 * 0.5 + L3])
    for r_max in workspace_r:
        arc_y = r_max * np.cos(theta_range)
        arc_z = H0 + r_max * np.sin(theta_range)
        ax.plot(arc_y, arc_z, "gray", linewidth=0.5, alpha=0.2, linestyle=":")

    # 标注关节角度
    textstr = (
        f"目标: ({x:.0f}, {y:.0f}, {z:.0f}) mm\n"
        f"印章角度: {wrist_angle}°\n"
        f"H0={H0} L1={L1} L2={L2} L3={L3} mm"
    )
    ax.text(
        0.02, 0.98, textstr, transform=ax.transAxes,
        fontsize=9, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    ax.legend(loc="lower right", fontsize=8)
    ax.set_title(f"WeArm 盖章轨迹仿真 — 目标 ({x}, {y}, {z}) mm")
    ax.set_xlim(-50, max(250, y + 80))
    ax.set_ylim(-20, H0 + L1 + L2 + L3 + 50)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"\n✅ 图片已保存: {save_path}")
    plt.show()


# ─── 动画 ──────────────────────────────────────────────────────────────────


def animate_stamping(
    x: float, y: float, z: float,
    wrist_angle: float = -90.0,
    lift_height: float = 40.0,
    save_path: str | None = None,
):
    """盖章过程动画"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Y (水平), mm")
    ax.set_ylabel("Z (垂直), mm")
    ax.add_patch(mpatches.Rectangle((-25, -10), 50, 10, color="gray", alpha=0.3))
    ax.axhline(y=0, color="saddlebrown", linestyle="--", alpha=0.5, linewidth=1)
    ax.plot(y, z, "rx", markersize=10)

    # 生成轨迹: 起抬 → 下降 → 下压(暂略，只做运动学)
    n_frames = 60
    z_path = np.concatenate([
        np.linspace(z + lift_height, z, n_frames // 2),  # 下降
        np.full(n_frames // 2, z),  # 到位停留
    ])

    ik_cache = {}
    for z_val in np.unique(z_path):
        ik_cache[z_val] = inverse_kinematics(x, y, z_val, wrist_angle=wrist_angle)

    arm_lines = None
    stamp_arrow = None
    stamp_bar = None

    def init():
        nonlocal arm_lines
        arm_lines, = ax.plot([], [], "-o", color="steelblue", lw=3, markersize=6)
        return [arm_lines]

    def update(frame):
        nonlocal arm_lines, stamp_arrow, stamp_bar
        z_val = z_path[frame]
        ik = ik_cache.get(z_val)
        if ik is None:
            return [arm_lines] if arm_lines else []

        angles = compute_all_joint_info(ik)
        joints = forward_kinematics(angles)
        ys = [p[0] for p in joints]
        zs = [p[1] for p in joints]
        arm_lines.set_data(ys, zs)

        # 清除旧的箭头和横线
        for artist in [stamp_arrow, stamp_bar]:
            if artist:
                artist.remove()
        stamp_arrow = None
        stamp_bar = None

        end = joints[-1]
        direction_rad = math.radians(wrist_angle)
        stamp_len = L3 * 0.6
        stamp_arrow = ax.annotate(
            "", xy=(end[0] + stamp_len * math.cos(direction_rad),
                    end[1] + stamp_len * math.sin(direction_rad)),
            xytext=end,
            arrowprops=dict(arrowstyle="->", color="red", lw=2),
        )
        perp = direction_rad + math.pi / 2
        half = L3 * 0.3
        stamp_bar, = ax.plot(
            [end[0] + half * math.cos(perp), end[0] - half * math.cos(perp)],
            [end[1] + half * math.sin(perp), end[1] - half * math.sin(perp)],
            color="red", lw=3,
        )

        ax.set_title(f"WeArm 盖章动画 — z={z_val:.0f}mm — 帧 {frame+1}/{n_frames}")
        artists = [arm_lines, stamp_bar]
        if stamp_arrow:
            artists.append(stamp_arrow)
        return artists

    anim = FuncAnimation(fig, update, frames=n_frames, init_func=init,
                         interval=50, blit=False, repeat=True)

    ax.set_xlim(-50, max(250, y + 80))
    ax.set_ylim(-20, H0 + L1 + L2 + L3 + 50)

    plt.tight_layout()
    if save_path:
        anim.save(save_path, writer="pillow", fps=10, dpi=100)
        print(f"\n✅ 动画已保存: {save_path}")
    plt.show()


# ─── CLI ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="WeArm 机械臂 2D 可视化仿真")
    parser.add_argument("--x", type=float, default=120, help="目标 X (前后), mm")
    parser.add_argument("--y", type=float, default=0, help="目标 Y (左右), mm")
    parser.add_argument("--z", type=float, default=0, help="目标 Z (高度), mm (0=工作面)")
    parser.add_argument("--wrist", type=float, default=-90, help="手腕角度, 度 (-90=竖直朝下)")
    parser.add_argument("--lift", type=float, default=40, help="抬起高度, mm")
    parser.add_argument("--animate", action="store_true", help="动画模式")
    parser.add_argument("--save", type=str, default=None, help="保存图片/动画路径")
    args = parser.parse_args()

    print(f"目标位置: ({args.x}, {args.y}, {args.z}) mm")
    print(f"手腕角度: {args.wrist}°")
    print(f"连杆参数: H0={H0} L1={L1} L2={L2} L3={L3} mm\n")

    # 验证 IK
    ik = inverse_kinematics(args.x, args.y, args.z, wrist_angle=args.wrist)
    if ik is None:
        print("❌ 目标超出工作空间！")
        return
    angles = compute_all_joint_info(ik)
    joints = forward_kinematics(angles)
    print(f"关节角度: 底座={angles[0]:.1f}°  大臂={angles[1]:.1f}°  "
          f"小臂={angles[2]:.1f}°  手腕={angles[3]:.1f}°")
    print(f"PWM: {ik}")
    print(f"末端位置: Y={joints[-1][0]:.1f}  Z={joints[-1][1]:.1f}")
    print()

    if args.animate:
        animate_stamping(args.x, args.y, args.z, args.wrist, args.lift, args.save)
    else:
        plot_stamp_trajectory(args.x, args.y, args.z, args.wrist, args.lift, args.save)


if __name__ == "__main__":
    main()
