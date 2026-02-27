"""
联系人模块的 Action 定义
"""
from typing import Optional
from pydantic import BaseModel, Field


class ContactAction(BaseModel):
    """联系人操作"""
    type: str = Field(default="", description="操作类型: contact_create/contact_query/contact_update/contact_delete")
    name: Optional[str] = Field(default=None, description="联系人姓名")
    phone: Optional[str] = Field(default=None, description="电话号码")
    birthday: Optional[str] = Field(default=None, description="生日，格式: MM-DD")
    remark: Optional[str] = Field(default=None, description="备注（如：大学同学、前同事）")
    extra: Optional[str] = Field(default=None, description="其他信息（爱好、QQ、邮箱、地址等）")
    query_field: Optional[str] = Field(default=None, description="查询的字段类型: phone/birthday/all")
