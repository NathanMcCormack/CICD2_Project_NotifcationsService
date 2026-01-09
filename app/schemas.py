from typing import Annotated, Optional, List
from pydantic import BaseModel, ConfigDict, StringConstraints

ReferenceStr = Annotated[str, StringConstraints(min_length=1, max_length=64)]
RecipientStr = Annotated[str, StringConstraints(min_length=3, max_length=255)]
ChannelStr = Annotated[str, StringConstraints(pattern=r"^(email|sms|push)$")]
MessageStr = Annotated[str, StringConstraints(min_length=1, max_length=500)]
StatusStr = Annotated[str, StringConstraints(min_length=1, max_length=20)]
ProviderStr = Annotated[str, StringConstraints(min_length=1, max_length=40)]
ResultStr = Annotated[str, StringConstraints(min_length=1, max_length=200)]

# ---------- Notifications ----------
class NotificationCreate(BaseModel):
    reference: ReferenceStr
    recipient: RecipientStr
    channel: ChannelStr
    message: MessageStr

class NotificationUpdate(BaseModel):
    recipient: Optional[RecipientStr] = None
    channel: Optional[ChannelStr] = None
    message: Optional[MessageStr] = None
    status: Optional[StatusStr] = None

class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference: ReferenceStr
    recipient: RecipientStr
    channel: ChannelStr
    message: MessageStr
    status: StatusStr

# ---------- Delivery Attempts ----------
class DeliveryCreate(BaseModel):
    provider: ProviderStr
    result: ResultStr
    attempt_no: int = 1
    notification_id: int

class DeliveryCreateForNotification(BaseModel):
    provider: ProviderStr
    result: ResultStr
    attempt_no: int = 1

class DeliveryUpdate(BaseModel):
    provider: Optional[ProviderStr] = None
    result: Optional[ResultStr] = None
    attempt_no: Optional[int] = None

class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider: ProviderStr
    result: ResultStr
    attempt_no: int
    notification_id: int

class DeliveryReadWithNotification(DeliveryRead):
    notification: Optional[NotificationRead] = None

class NotificationReadWithDeliveries(NotificationRead):
    deliveries: List[DeliveryRead] = []
