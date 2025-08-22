import uvicorn
from fastapi import FastAPI, Response, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import params_utils
import engine

import json

__pu = params_utils.ConfigManager()
logging = __pu.get_logger()

engine.generate_secret_files()

app = FastAPI()
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")

@app.get('/', response_class=RedirectResponse, status_code=302)
async def access_ui():
    return '/ui/snapshots.html'

@app.get('/api/snapshots')
async def get_snapshots(request: Request, response: Response, force_refresh='false'):
    return {
        "data": engine.get_all_snapshots(ignore_cache=force_refresh != 'false'),
        "config" : __pu.get_all_censored()
    }


@app.get(f"/api/repo/{'{repo}'}/files/{'{snapshot_id}'}")
async def get_files_from_snapshot(request: Request, response: Response, repo, snapshot_id, force_refresh='false'):
    metadata, data = engine.get_snapshot_files(repo=repo, snapshot_id=snapshot_id, ignore_cache=force_refresh != 'false')

    if data is None:
        response.status_code = 404
        return json.loads(metadata)

    return {
        "metadata": metadata,
        "data": data,
        "config" : __pu.get_all_censored()
    }


if __name__ == '__main__':
    uvicorn.run(app, port=__pu.get('app').get('listen_port'), host=__pu.get('app').get('listen_host'))
