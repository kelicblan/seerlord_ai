import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.json'
import zhTW from './locales/zh-TW.json'
import en from './locales/en.json'

export type MessageSchema = typeof zhCN

const savedLocale = localStorage.getItem('user-locale') || 'zh-CN'

const i18n = createI18n<[MessageSchema], 'zh-CN' | 'zh-TW' | 'en'>({
  legacy: false, // Vue 3 Composition API
  locale: savedLocale as 'zh-CN' | 'zh-TW' | 'en', // default locale
  fallbackLocale: 'en',
  messages: {
    'zh-CN': zhCN,
    'zh-TW': zhTW,
    en: en
  }
})

export default i18n