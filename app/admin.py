from sqladmin import Admin, ModelView
from .models import User, Location, MediaData, Driver, DriverLocation, Assignment
from .db import engine
from fastapi import FastAPI
from markupsafe import Markup

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.first_name, User.last_name,User.mobile]
class LocationAdmin(ModelView, model=Location):
    column_list = [Location.id, Location.user_id, Location.latitude, Location.longitude, Location.landmark]
    column_searchable_list = [Location.landmark]
    column_sortable_list = [Location.id, Location.user_id]
class MediaAdmin(ModelView, model=MediaData):
    column_list = [
        MediaData.id,
        MediaData.user_id,
        MediaData.mobile_number,
        MediaData.image_path,
        MediaData.audio_path
    ]

    column_formatters = {
        "image_path": lambda m, attr: Markup(
            f'<img src="/{attr}" style="max-height: 100px;" />') if attr else ""
    }
class DriverAdmin(ModelView,model=Driver):
    column_list = "__all__"
class DriverLocationAdmin(ModelView,model=DriverLocation):
    column_list = "__all__"

class AssignmentAdmin(ModelView,model=Assignment):
    column_list = "__all__"
def setup_admin(app: FastAPI):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(LocationAdmin)
    admin.add_view(MediaAdmin)
    admin.add_view(DriverAdmin)
    admin.add_view(DriverLocationAdmin)
    admin.add_view(AssignmentAdmin)
