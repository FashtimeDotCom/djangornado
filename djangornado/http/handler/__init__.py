# -*- coding:utf-8 -*-

import traceback
from tornado.web import HTTPError
from tornado.web import RequestHandler
from tornado.web import asynchronous
from djangornado.core.exceptions import NoReturnResponseError
from djangornado.http.request import DjangornadoRequest
from djangornado.utils.importlib import import_module
from djangornado.conf import settings, urlpatterns
from djangornado.middleware import middleware

class DjangornadoHandler(RequestHandler):
    def _handle_request_exception(self, e):
        if settings.has_key("DEBUG") and settings.DEBUG is True:
            exstr = traceback.format_exc()
            self.write("""
                <p><h2>Djangornado Error</h2></p>
                <p>Error Msg:</p><p>%s</p><br>
                <p>Error:</p>
                <div>%s</div>
            """ %(str(e), str(exstr).replace("\n", "<br>")))
        else:
            raise HTTPError(500)
    
    def _execute(self, transforms, *args, **kwargs):
        self._dt_request = DjangornadoRequest(self, *args, **kwargs)
        try:
            for processer in middleware.request_middleware:
                response = processer(self._dt_request)
                if response:
                    self._render_response(response)
                    self.finish()
        except Exception, e:
            self._handle_request_exception(e)
        super(DjangornadoHandler, self)._execute(transforms, *args, **kwargs)
    
    def finish(self, chunk = None):
        try:
            for processer in middleware.response_middleware:
                processer(self._dt_request)
        except Exception, e:
            self._handle_request_exception(e)
        super(DjangornadoHandler, self).finish(chunk)

    def get_from_urls(self, pattern):
        is_asyn = self._dt_request.get_argument("asyn", False)
        callback = urlpatterns.callback(pattern)
        if callback:
            return callback, is_asyn
        raise HTTPError(404)
    
    def _syn_call(self, callback_func, request):
        self._render_response(callback_func(request))

    @asynchronous
    def _asyn_call(self, callback_func, request):
        result = callback_func(request)
        self._callback(result)
    
    def _callback(self, result):
        self._render_response(result)
        self.finish()
    
    def _render_response(self, response):
        try:
            if response is None:
                raise NoReturnResponseError("No response return")
            response.return_response(self)
        except Exception,e:
            self._handle_request_exception(e)
    
    def get(self, pattern):
        callback_func, asyn = self.get_from_urls(pattern)
        if callback_func:
            (self._asyn_call if asyn else self._syn_call)(callback_func, self._dt_request)
    
    def post(self, pattern):
        self.get(pattern)