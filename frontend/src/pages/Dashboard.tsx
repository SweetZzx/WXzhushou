import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, Users, Bell, Plus } from 'lucide-react'
import { scheduleApi, contactApi, type Schedule, type Contact } from '../api'

export default function Dashboard() {
  const [todaySchedules, setTodaySchedules] = useState<Schedule[]>([])
  const [upcomingBirthdays, setUpcomingBirthdays] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const today = new Date().toISOString().split('T')[0]
      const [schedules, contacts] = await Promise.all([
        scheduleApi.list(today),
        contactApi.list(),
      ])
      setTodaySchedules(schedules as unknown as Schedule[])
      setUpcomingBirthdays((contacts as unknown as Contact[]).filter((c: Contact) => c.birthday).slice(0, 3))
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500">加载中...</div>
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">首页概览</h1>

      {/* 快捷操作 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link
          to="/schedule"
          className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition group"
        >
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition">
            <Calendar className="text-primary-600" size={20} />
          </div>
          <p className="mt-3 font-medium text-gray-800">日程</p>
          <p className="text-sm text-gray-500">管理日程安排</p>
        </Link>

        <Link
          to="/contacts"
          className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition group"
        >
          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition">
            <Users className="text-green-600" size={20} />
          </div>
          <p className="mt-3 font-medium text-gray-800">联系人</p>
          <p className="text-sm text-gray-500">管理联系人信息</p>
        </Link>

        <Link
          to="/settings"
          className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition group"
        >
          <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center group-hover:bg-orange-200 transition">
            <Bell className="text-orange-600" size={20} />
          </div>
          <p className="mt-3 font-medium text-gray-800">提醒设置</p>
          <p className="text-sm text-gray-500">配置提醒方式</p>
        </Link>

        <div className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition cursor-pointer group">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition">
            <Plus className="text-purple-600" size={20} />
          </div>
          <p className="mt-3 font-medium text-gray-800">快速添加</p>
          <p className="text-sm text-gray-500">通过微信添加</p>
        </div>
      </div>

      {/* 今日日程 */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">今日日程</h2>
          <Link to="/schedule" className="text-primary-600 text-sm hover:underline">
            查看全部
          </Link>
        </div>

        {todaySchedules.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Calendar size={40} className="mx-auto mb-2 opacity-50" />
            <p>今日暂无日程安排</p>
          </div>
        ) : (
          <div className="space-y-3">
            {todaySchedules.map((schedule) => (
              <div
                key={schedule.id}
                className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg"
              >
                <div className="text-primary-600 font-medium">
                  {formatTime(schedule.scheduled_time)}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{schedule.title}</p>
                  {schedule.description && (
                    <p className="text-sm text-gray-500">{schedule.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 近期生日 */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">近期生日</h2>
          <Link to="/contacts" className="text-primary-600 text-sm hover:underline">
            查看全部
          </Link>
        </div>

        {upcomingBirthdays.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Users size={40} className="mx-auto mb-2 opacity-50" />
            <p>暂无近期生日</p>
          </div>
        ) : (
          <div className="space-y-3">
            {upcomingBirthdays.map((contact) => (
              <div
                key={contact.id}
                className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg"
              >
                <div className="w-10 h-10 bg-pink-100 rounded-full flex items-center justify-center">
                  <span className="text-pink-600 font-medium">
                    {contact.name.charAt(0)}
                  </span>
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{contact.name}</p>
                  <p className="text-sm text-gray-500">生日: {contact.birthday}</p>
                </div>
                {contact.remark && (
                  <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                    {contact.remark}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
