import api from './client'

// 类型定义
export interface Schedule {
  id: number
  title: string
  scheduled_time: string
  description?: string
  created_at: string
}

export interface Contact {
  id: number
  name: string
  phone?: string
  birthday?: string
  remark?: string
  extra?: string
  created_at: string
}

export interface UserSettings {
  daily_reminder_enabled: boolean
  daily_reminder_time: string
  pre_reminder_enabled: boolean
  pre_reminder_minutes: number
  birthday_reminder_enabled: boolean
  birthday_reminder_days: number
}

export interface UserSubscription {
  module_id: string
  module_name: string
  enabled: boolean
}

// 认证 API
export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ token: string; user: { id: string; username: string } }>('/auth/login', { username, password }),

  register: (username: string, password: string) =>
    api.post<{ token: string; user: { id: string; username: string } }>('/auth/register', { username, password }),

  getWechatBindUrl: () =>
    api.get<{ qr_url: string; bind_token: string }>('/auth/wechat/bind'),

  checkWechatBind: (bindToken: string) =>
    api.get<{ bound: boolean }>(`/auth/wechat/check/${bindToken}`),
}

// 日程 API
export const scheduleApi = {
  list: (date?: string) =>
    api.get<Schedule[]>('/schedules', { params: { date } }),

  create: (data: { title: string; scheduled_time: string; description?: string }) =>
    api.post<Schedule>('/schedules', data),

  update: (id: number, data: Partial<{ title: string; scheduled_time: string; description: string }>) =>
    api.put<Schedule>(`/schedules/${id}`, data),

  delete: (id: number) =>
    api.delete(`/schedules/${id}`),
}

// 联系人 API
export const contactApi = {
  list: (keyword?: string) =>
    api.get<Contact[]>('/contacts', { params: { keyword } }),

  create: (data: { name: string; phone?: string; birthday?: string; remark?: string; extra?: string }) =>
    api.post<Contact>('/contacts', data),

  update: (id: number, data: Partial<{ name: string; phone: string; birthday: string; remark: string; extra: string }>) =>
    api.put<Contact>(`/contacts/${id}`, data),

  delete: (id: number) =>
    api.delete(`/contacts/${id}`),
}

// 设置 API
export const settingsApi = {
  get: () =>
    api.get<UserSettings>('/settings'),

  update: (data: Partial<UserSettings>) =>
    api.put<UserSettings>('/settings', data),
}

// 订阅 API
export const subscriptionApi = {
  list: () =>
    api.get<UserSubscription[]>('/subscriptions'),

  toggle: (moduleId: string, enabled: boolean) =>
    api.post('/subscriptions/toggle', { module_id: moduleId, enabled }),
}
