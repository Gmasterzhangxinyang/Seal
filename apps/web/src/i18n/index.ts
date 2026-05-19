import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import zhCommon from './locales/zh/common.json'
import zhNav from './locales/zh/nav.json'
import zhAuth from './locales/zh/auth.json'
import zhStamp from './locales/zh/stamp.json'
import zhLogs from './locales/zh/logs.json'
import zhReview from './locales/zh/review.json'
import zhAdmin from './locales/zh/admin.json'
import zhApplications from './locales/zh/applications.json'
import zhCalibration from './locales/zh/calibration.json'
import zhChat from './locales/zh/chat.json'

import enCommon from './locales/en/common.json'
import enNav from './locales/en/nav.json'
import enAuth from './locales/en/auth.json'
import enStamp from './locales/en/stamp.json'
import enLogs from './locales/en/logs.json'
import enReview from './locales/en/review.json'
import enAdmin from './locales/en/admin.json'
import enApplications from './locales/en/applications.json'
import enCalibration from './locales/en/calibration.json'
import enChat from './locales/en/chat.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      zh: {
        common: zhCommon,
        nav: zhNav,
        auth: zhAuth,
        stamp: zhStamp,
        logs: zhLogs,
        review: zhReview,
        admin: zhAdmin,
        applications: zhApplications,
        calibration: zhCalibration,
        chat: zhChat,
      },
      en: {
        common: enCommon,
        nav: enNav,
        auth: enAuth,
        stamp: enStamp,
        logs: enLogs,
        review: enReview,
        admin: enAdmin,
        applications: enApplications,
        calibration: enCalibration,
        chat: enChat,
      },
    },
    fallbackLng: 'zh',
    defaultNS: 'common',
    ns: ['common', 'nav', 'auth', 'stamp', 'logs', 'review', 'admin', 'applications', 'calibration', 'chat'],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'mec202-lang',
      caches: ['localStorage'],
    },
  })

export default i18n
