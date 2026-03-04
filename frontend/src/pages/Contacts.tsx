import { useEffect, useState } from 'react'
import { Plus, Search, Trash2, Edit2, Phone, Cake, Tag } from 'lucide-react'
import { contactApi, type Contact as ContactType } from '../api'

export default function Contacts() {
  const [contacts, setContacts] = useState<ContactType[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingContact, setEditingContact] = useState<ContactType | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    birthday: '',
    remark: '',
    extra: '',
  })

  useEffect(() => {
    loadContacts()
  }, [])

  const loadContacts = async () => {
    try {
      const data = await contactApi.list()
      setContacts(data as unknown as ContactType[])
    } catch (error) {
      console.error('加载联系人失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    try {
      const data = await contactApi.list(searchKeyword || undefined)
      setContacts(data as unknown as ContactType[])
    } catch (error) {
      console.error('搜索失败:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingContact) {
        await contactApi.update(editingContact.id, formData)
      } else {
        await contactApi.create(formData)
      }
      setShowAddModal(false)
      setEditingContact(null)
      setFormData({ name: '', phone: '', birthday: '', remark: '', extra: '' })
      loadContacts()
    } catch (error) {
      console.error('保存联系人失败:', error)
    }
  }

  const handleEdit = (contact: ContactType) => {
    setEditingContact(contact)
    setFormData({
      name: contact.name,
      phone: contact.phone || '',
      birthday: contact.birthday || '',
      remark: contact.remark || '',
      extra: contact.extra || '',
    })
    setShowAddModal(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个联系人吗？')) return
    try {
      await contactApi.delete(id)
      loadContacts()
    } catch (error) {
      console.error('删除联系人失败:', error)
    }
  }

  const closeModal = () => {
    setShowAddModal(false)
    setEditingContact(null)
    setFormData({ name: '', phone: '', birthday: '', remark: '', extra: '' })
  }

  // 按备注分组
  const groupedContacts = contacts.reduce((groups, contact) => {
    const key = contact.remark || '未分类'
    if (!groups[key]) {
      groups[key] = []
    }
    groups[key].push(contact)
    return groups
  }, {} as Record<string, ContactType[]>)

  if (loading) {
    return <div className="text-center py-12 text-gray-500">加载中...</div>
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">联系人管理</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
        >
          <Plus size={20} />
          添加联系人
        </button>
      </div>

      {/* 搜索栏 */}
      <div className="flex gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
            placeholder="搜索联系人..."
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition font-medium"
        >
          搜索
        </button>
      </div>

      {Object.keys(groupedContacts).length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <Search size={48} className="mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">暂无联系人</p>
          <p className="text-sm text-gray-400 mt-2">点击上方按钮添加新联系人</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedContacts).map(([group, items]) => (
            <div key={group}>
              <h3 className="text-sm font-medium text-gray-500 mb-3 flex items-center gap-2">
                <Tag size={16} />
                {group}
                <span className="bg-gray-200 px-2 py-0.5 rounded text-xs">{items.length}</span>
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                {items.map((contact) => (
                  <div
                    key={contact.id}
                    className="bg-white rounded-xl shadow-sm border p-4 hover:shadow-md transition"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                          <span className="text-primary-600 font-bold text-lg">
                            {contact.name.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-800">{contact.name}</h4>
                          {contact.remark && (
                            <span className="text-xs bg-primary-50 text-primary-600 px-2 py-0.5 rounded">
                              {contact.remark}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleEdit(contact)}
                          className="p-2 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => handleDelete(contact.id)}
                          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>

                    <div className="mt-4 space-y-2">
                      {contact.phone && (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <Phone size={14} className="text-gray-400" />
                          <span>{contact.phone}</span>
                        </div>
                      )}
                      {contact.birthday && (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <Cake size={14} className="text-gray-400" />
                          <span>{contact.birthday}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 添加/编辑弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold text-gray-800 mb-4">
              {editingContact ? '编辑联系人' : '添加联系人'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  姓名 *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  电话
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="手机号码"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  生日
                </label>
                <input
                  type="text"
                  value={formData.birthday}
                  onChange={(e) => setFormData({ ...formData, birthday: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="格式: MM-DD，例如 03-15"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  备注
                </label>
                <input
                  type="text"
                  value={formData.remark}
                  onChange={(e) => setFormData({ ...formData, remark: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="例如：家人、同事、朋友"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  其他信息
                </label>
                <textarea
                  value={formData.extra}
                  onChange={(e) => setFormData({ ...formData, extra: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-none"
                  rows={2}
                  placeholder="爱好、地址等..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="flex-1 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition font-medium"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium"
                >
                  {editingContact ? '保存' : '添加'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
