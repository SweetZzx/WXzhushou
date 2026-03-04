import { useEffect, useState } from 'react'
import { Bell, Calendar, Cake, MessageCircle, QrCode, Check } from 'lucide-react'
import { settingsApi, subscriptionApi, type UserSettings, type UserSubscription } from '../api'

export default function Settings() {
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [subscriptions, setSubscriptions] = useState<UserSubscription[]>([])
  const [loading, setLoading] = useState(true)
  const [showQr, setShowQr] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [settingsData, subData] = await Promise.all([
        settingsApi.get(),
        subscriptionApi.list(),
      ])
      setSettings(settingsData as unknown as UserSettings)
      setSubscriptions(subData as unknown as UserSubscription[])
    } catch (error) {
      console.error('加载设置失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSettingChange = async (key: keyof UserSettings, value: boolean | number | string) => {
    if (!settings) return
    try {
      const updated = await settingsApi.update({ [key]: value })
      setSettings(updated as unknown as UserSettings)
    } catch (error) {
      console.error('更新设置失败:', error)
    }
  }

  const handleSubscriptionToggle = async (moduleId: string, enabled: boolean) => {
    try {
      await subscriptionApi.toggle(moduleId, enabled)
      setSubscriptions(subs =>
        subs.map(s => (s.module_id === moduleId ? { ...s, enabled } : s))
      )
    } catch (error) {
      console.error('更新订阅失败:', error)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">加载中...</div>
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">设置</h1>

      {/* 功能模块订阅 */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">功能模块</h2>
        <div className="space-y-4">
          {subscriptions.map((sub) => (
            <div
              key={sub.module_id}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {sub.module_id === 'schedule' ? (
                  <Calendar className="text-primary-600" size={20} />
                ) : (
                  <Cake className="text-pink-600" size={20} />
                )}
                <div>
                  <p className="font-medium text-gray-800">{sub.module_name}</p>
                  <p className="text-sm text-gray-500">
                    {sub.module_id === 'schedule' ? '日程管理与提醒' : '联系人与生日提醒'}
                  </p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={sub.enabled}
                  onChange={(e) => handleSubscriptionToggle(sub.module_id, e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* 日程提醒设置 */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="text-primary-600" size={20} />
          <h2 className="text-lg font-semibold text-gray-800">日程提醒</h2>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">每日提醒</p>
              <p className="text-sm text-gray-500">每天定时提醒当天的日程</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.daily_reminder_enabled ?? false}
                onChange={(e) => handleSettingChange('daily_reminder_enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
            </label>
          </div>

          {settings?.daily_reminder_enabled && (
            <div className="flex items-center justify-between pl-4 border-l-2 border-primary-200">
              <p className="text-sm text-gray-600">提醒时间</p>
              <input
                type="time"
                value={settings?.daily_reminder_time || '08:00'}
                onChange={(e) => handleSettingChange('daily_reminder_time', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              />
            </div>
          )}

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">日程前提醒</p>
              <p className="text-sm text-gray-500">日程开始前提醒</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.pre_reminder_enabled ?? false}
                onChange={(e) => handleSettingChange('pre_reminder_enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
            </label>
          </div>

          {settings?.pre_reminder_enabled && (
            <div className="flex items-center justify-between pl-4 border-l-2 border-primary-200">
              <p className="text-sm text-gray-600">提前时间（分钟）</p>
              <input
                type="number"
                min={5}
                max={120}
                value={settings?.pre_reminder_minutes || 30}
                onChange={(e) => handleSettingChange('pre_reminder_minutes', parseInt(e.target.value))}
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
              />
            </div>
          )}
        </div>
      </div>

      {/* 生日提醒设置 */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center gap-3 mb-4">
          <Cake className="text-pink-600" size={20} />
          <h2 className="text-lg font-semibold text-gray-800">生日提醒</h2>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">生日提醒</p>
              <p className="text-sm text-gray-500">联系人生日前提醒</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.birthday_reminder_enabled ?? false}
                onChange={(e) => handleSettingChange('birthday_reminder_enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-pink-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-pink-600"></div>
            </label>
          </div>

          {settings?.birthday_reminder_enabled && (
            <div className="flex items-center justify-between pl-4 border-l-2 border-pink-200">
              <p className="text-sm text-gray-600">提前天数</p>
              <select
                value={settings?.birthday_reminder_days || 7}
                onChange={(e) => handleSettingChange('birthday_reminder_days', parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500 outline-none"
              >
                <option value={1}>提前1天</option>
                <option value={3}>提前3天</option>
                <option value={7}>提前1周</option>
                <option value={14}>提前2周</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* 微信绑定 */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center gap-3 mb-4">
          <MessageCircle className="text-green-600" size={20} />
          <h2 className="text-lg font-semibold text-gray-800">微信绑定</h2>
        </div>

        {!showQr ? (
          <div>
            <p className="text-gray-600 mb-4">
              绑定微信后，可以通过微信语音/文字管理日程和联系人
            </p>
            <button
              onClick={() => setShowQr(true)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
            >
              <QrCode size={20} />
              获取绑定二维码
            </button>
          </div>
        ) : (
          <div className="text-center">
            <div className="w-48 h-48 bg-gray-100 rounded-lg mx-auto mb-4 flex items-center justify-center">
              <QrCode size={80} className="text-gray-400" />
            </div>
            <p className="text-sm text-gray-500 mb-2">使用微信扫描二维码绑定</p>
            <div className="flex items-center justify-center gap-2 text-green-600">
              <Check size={20} />
              <span>等待扫码绑定...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
