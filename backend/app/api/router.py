from fastapi import APIRouter
from .routes import events, market, risk, signals, simulation, supply_chain, chatbot, users, news, auth, forecast, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(market.router, prefix="/market", tags=["Markets"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk & GTI"])
api_router.include_router(signals.router, prefix="/signals", tags=["Trading Signals"])
api_router.include_router(simulation.router, prefix="/simulation", tags=["Simulation"])
api_router.include_router(supply_chain.router, prefix="/supply-chain", tags=["Supply Chain"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(chatbot.router, prefix="/chat", tags=["Chat"])
api_router.include_router(news.router, prefix="/news", tags=["News"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSockets"])
