import { useEffect, useState, useCallback } from 'react'
import { apiFetch, apiDelete } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import type { UserItem } from '@/types/api'

export function UsersPage() {
  const currentUser = useAuthStore((s) => s.user)
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<UserItem[]>('/users')
      setUsers(data)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleDelete = async (username: string) => {
    if (!confirm(`确定删除用户 "${username}" 吗？`)) return
    try {
      await apiDelete(`/users/${username}`)
      setUsers((prev) => prev.filter((u) => u.username !== username))
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-9 h-9 border-4 border-gray-200 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  const roleLabel: Record<string, string> = {
    admin: '管理员',
    reviewer: '复审员',
    operator: '操作员',
  }

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">用户管理</h2>
      <div className="bg-card rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left px-4 py-3 font-medium">用户名</th>
              <th className="text-left px-4 py-3 font-medium">邮箱</th>
              <th className="text-left px-4 py-3 font-medium">角色</th>
              <th className="text-left px-4 py-3 font-medium">注册时间</th>
              <th className="text-right px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isSelf = u.username === currentUser?.username
              return (
                <tr key={u.username} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{u.username}</td>
                  <td className="px-4 py-3 text-muted-foreground">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className="inline-block px-2 py-0.5 rounded text-xs bg-primary/10 text-primary">
                      {roleLabel[u.role] || u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{u.created_at}</td>
                  <td className="px-4 py-3 text-right">
                    {isSelf ? (
                      <span className="text-xs text-muted-foreground">当前用户</span>
                    ) : (
                      <button
                        onClick={() => handleDelete(u.username)}
                        className="text-xs text-red-500 hover:text-red-700 transition"
                      >
                        删除
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  暂无用户
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
