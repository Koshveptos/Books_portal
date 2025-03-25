from fastapi import FastAPI



app = FastAPI()

@app.get('/hhh')
def get_hhh():
    return {'404':'suck my dick'}






