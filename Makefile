NotificationServiceAPP = app.main:app 

install: 
	pip install -r requirements.txt 

runNotification: 
	python -m uvicorn $(NotificationServiceAPP) --host 0.0.0.0 --port 8000 --reload 

test: 
	python -m pytest -q
