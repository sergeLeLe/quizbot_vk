import typing
import uuid
from hashlib import sha256
from typing import Optional

from app.base.base_accessor import BaseAccessor
from app.admin.models import Admin, AdminModel

if typing.TYPE_CHECKING:
    from app.web.app import Application


class AdminAccessor(BaseAccessor):
    async def connect(self, app: "Application"):
        self.admins = []
        await super().connect(app)
        admin = await self.create_admin(
            email=app.config.admin.email, password=app.config.admin.password
        )
        await self.add_admin(admin)

    async def get_by_email(self, email: str) -> Optional[Admin]:
        res = await AdminModel.query.where(
            AdminModel.email == email
        ).gino.first()
        if not res:
            return None
        res = res.to_dict()
        return await self.create_admin(email=res['email'], password=res['password'], id_=res['id'])

    # admins
    async def create_admin(self, email: str, password: str, id_: int = None) -> Admin:
        self.admins.append(
            Admin(
                id=id_ if id_ else len(self.admins) + 1,
                email=email,
                password=password
            )
        )
        return self.admins[-1]

    async def add_admin(self, admin: Admin):
        res = await AdminModel.query.where(
            AdminModel.email == admin.email
        ).gino.all()
        if not res:
            await AdminModel.create(
                id=admin.id,
                email=admin.email,
                password=sha256(admin.password.encode()).hexdigest(),
            )
