import { useEffect, useState } from 'react'
import { Plus, Trash2, Calendar as CalendarIcon } from 'lucide-react'
import { scheduleApi, type Schedule as ScheduleType } from '../api'

export default function Schedule() {
  const [schedules, setSchedules] = useState<ScheduleType[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newSchedule, setNewSchedule] = useState({
    title: '',
    scheduled_time: '',
    description: '',
  })

  useEffect(() => {
    loadSchedules()
  }, [])

  const loadSchedules = async () => {
    try {
      const data = await scheduleApi.list()
      setSchedules(data as unknown as ScheduleType[])
    } catch (error) {
      console.error('加载日程失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await scheduleApi.create(newSchedule)
      setShowAddModal(false)
      setNewSchedule({ title: '', scheduled_time: '', description: '' })
      loadSchedules()
    } catch (error) {
      console.error('添加日程失败:', error)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个日程吗？')) return
    try {
      await scheduleApi.delete(id)
      loadSchedules()
    } catch (error) {
      console.error('删除日程失败:', error)
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  // 按日期分组
  const groupedSchedules = schedules.reduce((groups, schedule) => {
    const date = new Date(schedule.scheduled_time).toLocaleDateString('zh-CN')
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(schedule)
    return groups
  }, {} as Record<string, ScheduleType[]>)

  if (loading) {
    return <div className="text-center py-12 text-gray-500">加载中...</div>
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">日程管理</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          <Plus size={20} />
          添加日程
        </button>
      </div>

      {Object.keys(groupedSchedules).length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <CalendarIcon size={48} className="mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">暂无日程安排</p>
          <p className="text-sm text-gray-400 mt-2">点击上方按钮添加新日程</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedSchedules).map(([date, items]) => (
            <div key={date}>
              <h3 className="text-sm font-medium text-gray-500 mb-3">{date}</h3>
              <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                {items.map((schedule, index) => (
                  <div
                    key={schedule.id}
                    className={`flex items-center gap-4 p-4 ${
                      index !== items.length - 1 ? 'border-b' : ''
                    }`}
                  >
                    <div className="text-primary-600 font-medium w-16">
                      {formatTime(schedule.scheduled_time)}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">{schedule.title}</p>
                      {schedule.description && (
                        <p className="text-sm text-gray-500">{schedule.description}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleDelete(schedule.id)}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 添加日程弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold text-gray-800 mb-4">添加日程</h2>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  日程标题
                </label>
                <input
                  type="text"
                  value={newSchedule.title}
                  onChange={(e) => setNewSchedule({ ...newSchedule, title: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="例如：开会、约会"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  时间
                </label>
                <input
                  type="datetime-local"
                  value={newSchedule.scheduled_time}
                  onChange={(e) => setNewSchedule({ ...newSchedule, scheduled_time: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  备注（可选）
                </label>
                <textarea
                  value={newSchedule.description}
                  onChange={(e) => setNewSchedule({ ...newSchedule, description: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-none"
                  rows={3}
                  placeholder="补充说明..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition font-medium"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium"
                >
                  添加
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
