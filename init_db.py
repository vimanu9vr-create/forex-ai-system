from app.database import (engine,Base)

from app.models.trade_model import (Trade)

Base.metadata.create_all(bind=engine)
print("Database initialized successfully.")