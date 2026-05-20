"""
Storage routes.

  HealthRoutes  GET /health
  FileRoutes    POST/GET /internal/* (presign, save, list)
"""
from app.Routes.HealthRoutes import router as health_router
from app.Routes.FileRoutes import router as file_router

__all__ = ["health_router", "file_router"]