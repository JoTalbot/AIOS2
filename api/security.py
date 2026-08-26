"""Canonical control-plane authentication context and RBAC."""
from dataclasses import dataclass
from enum import Enum
import hmac
from typing import Optional
from uuid import uuid4
from fastapi import HTTPException, Request
from .auth_config import ControlPlaneAuthConfig
class OperatorRole(str,Enum):
    VIEWER="viewer"; OPERATOR="operator"; ADMIN="admin"
    def allows(self,minimum): return {OperatorRole.VIEWER:0,OperatorRole.OPERATOR:1,OperatorRole.ADMIN:2}[self] >= {OperatorRole.VIEWER:0,OperatorRole.OPERATOR:1,OperatorRole.ADMIN:2}[minimum]
@dataclass(frozen=True)
class SecurityContext: actor:str; role:OperatorRole; correlation_id:str
def authenticate(request:Request,config:Optional[ControlPlaneAuthConfig]=None):
    if config is None:
        try: config=ControlPlaneAuthConfig.from_env()
        except RuntimeError: return None
    authorization=request.headers.get("authorization","")
    if not authorization.startswith("Bearer "): return None
    supplied=authorization[7:]
    if not supplied or not hmac.compare_digest(supplied,config.token): return None
    correlation_id=request.headers.get("x-correlation-id") or str(uuid4())
    if len(correlation_id)>128: return None
    return SecurityContext(config.actor,OperatorRole(config.role),correlation_id)
def require_role(request:Request,minimum:OperatorRole):
    context=authenticate(request)
    if context is None: raise HTTPException(status_code=403,detail="operator authorization required")
    if not context.role.allows(minimum): raise HTTPException(status_code=403,detail=f"role {minimum.value} required")
    request.state.operator_context=context; return context
