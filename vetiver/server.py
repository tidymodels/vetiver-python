from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

import uvicorn
import requests
import pandas as pd
from typing import Callable, Optional, Union, List

from .vetiver_model import VetiverModel
from .utils import _jupyter_nb


class VetiverAPI:
    """Create model aware API

    Attributes
    ----------
    model :  VetiverModel
        Model to be deployed in API
    check_ptype : bool
        Determine if data prototype should be enforced
    port :  int
        Port for deployment
    host :
        Host address
    app_factory :
        Type of API to be deployed
    app :
        API that is deployed
    """

    app = None

    def __init__(
        self,
        model: VetiverModel,
        check_ptype: bool = True,
        port: Optional[int] = 8000,
        host="127.0.0.1",
        app_factory=FastAPI,
    ) -> None:
        self.model = model
        self.port = port
        self.host = host
        self.check_ptype = check_ptype
        self.app_factory = app_factory
        self.app = self._init_app()

    def _init_app(self):
        app = self.app_factory()
        app.openapi = self._custom_openapi

        @app.get("/", include_in_schema=False)
        def docs_redirect():
            return RedirectResponse("/__docs__")

        @app.get("/ping", include_in_schema=True)
        async def ping():
            return {"ping": "pong"}

        @app.get("/__docs__", response_class=HTMLResponse, include_in_schema=False)
        async def rapidoc_pg():
            return f"""
                    <!doctype html>
                    <html>
                        <head>
                        <meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1,user-scalable=yes">
                        <title>RapiDoc</title>
                        <script type="module" src="https://unpkg.com/rapidoc@9.1.3/dist/rapidoc-min.js"></script>
                        </script></head>
                        <body>
                            <rapi-doc spec-url="{app.openapi_url}"
                            id="thedoc" render-style="read" schema-style="tree" 
                            show-components="true" show-info="true" show-header="true" 
                            allow-search="true"
                            show-side-nav="false"
                            allow-authentication="false" update-route="false" match-type="regex"
                            theme="light"
                            header-color="#F2C6AC"
                            primary-color = "#8C2D2D">
                            <img
                            slot="logo"
                            width="55"
                            src="https://raw.githubusercontent.com/rstudio/hex-stickers/master/SVG/vetiver.svg"
                            </rapi-doc>
                        </body>
                    </html>
            """

        if self.check_ptype == True:

            @app.post("/predict/")
            async def prediction(
                input_data: Union[self.model.ptype, List[self.model.ptype]]
            ):

                if isinstance(input_data, List):
                    served_data = _batch_data(input_data)
                else:
                    served_data = _prepare_data(input_data)

                y = self.model.handler_predict(
                    served_data, check_ptype=self.check_ptype
                )

                return {"prediction": y.tolist()}

        else:

            @app.post("/predict/")
            async def prediction(input_data: Request):
                y = await input_data.json()
                prediction = self.model.handler_predict(y, check_ptype=self.check_ptype)

                return {"prediction": prediction.tolist()}

        return app

    def vetiver_post(
        self, endpoint_fx: Callable, endpoint_name: str = "custom_endpoint"
    ):
        """Create new POST endpoint

        Parameters
        ----------
        endpoint_fx : typing.Callable
            Custom function to be run at endpoint
        endpoint_name : str
            Name of endpoint

        Returns
        -------
        dict
            Key: endpoint_name Value: Output of endpoint_fx, in list format
        """
        if self.check_ptype == True:

            @self.app.post("/" + endpoint_name + "/")
            async def custom_endpoint(input_data: self.model.ptype):
                y = _prepare_data(input_data)
                new = endpoint_fx(pd.Series(y))
                return {endpoint_name: new.tolist()}

        else:

            @self.app.post("/" + endpoint_name + "/")
            async def custom_endpoint(input_data: Request):
                y = await input_data.json()
                new = endpoint_fx(pd.Series(y))

                return {endpoint_name: new.tolist()}

    def run(self):
        """Start API"""
        _jupyter_nb()
        uvicorn.run(self.app, port=self.port, host=self.host)

    def _custom_openapi(self):
        if self.app.openapi_schema:
            return self.app.openapi_schema
        openapi_schema = get_openapi(
            title=self.model.model_name + " model API",
            version="0.1.3",
            description=self.model.description,
            routes=self.app.routes,
        )
        openapi_schema["info"]["x-logo"] = {"url": "../docs/figures/logo.svg"}
        self.app.openapi_schema = openapi_schema
        return self.app.openapi_schema

def predict(endpoint, data: dict, **kw):
    """Make a prediction from model endpoint

    Parameters
    ----------
    endpoint :
        URI path to endpoint
    data : dict
        Name of endpoint

    Returns
    -------
    dict
        Key: endpoint_name Value: Output of endpoint_fx, in list format
    """
    if isinstance(data, pd.DataFrame):
        data = data.to_json(orient="records")
        response = requests.post(endpoint, data=data, **kw)
    else:
        response = requests.post(endpoint, json=data, **kw)

    return response.json()


def _prepare_data(pred_data):
    served_data = []
    for key, value in pred_data:
        served_data.append(value)
    return served_data


def _batch_data(pred_data):
    columns = pred_data[0].dict().keys()

    data = [line.dict() for line in pred_data]

    served_data = pd.DataFrame(data, columns=columns)
    return served_data


def vetiver_endpoint(url="http://127.0.0.1:8000/predict"):
    """Wrap url where VetiverModel will be deployed

    Parameters
    ----------
    url : str
        URI path to endpoint

    Returns
    -------
    url : str
        URI path to endpoint
    """
    return url
