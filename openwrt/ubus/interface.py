# -*- coding: utf-8 -*-
"""Client for the OpenWrt ubus API."""

import json
import logging

import requests

from .const import (
    API_DEF_DEBUG,
    API_DEF_SESSION_ID,
    API_DEF_TIMEOUT,
    API_DEF_VERIFY,
    API_ERROR,
    API_MESSAGE,
    API_METHOD_GET,
    API_METHOD_GET_CLIENTS,
    API_METHOD_LOGIN,
    API_METHOD_READ,
    API_PARAM_CONFIG,
    API_PARAM_PASSWORD,
    API_PARAM_PATH,
    API_PARAM_TYPE,
    API_PARAM_USERNAME,
    API_RESULT,
    API_RPC_CALL,
    API_RPC_ID,
    API_RPC_LIST,
    API_RPC_VERSION,
    API_SUBSYS_DHCP,
    API_SUBSYS_FILE,
    API_SUBSYS_HOSTAPD,
    API_SUBSYS_SESSION,
    API_SUBSYS_UCI,
    API_UBUS_RPC_SESSION,
    HTTP_STATUS_OK,
)

_LOGGER = logging.getLogger(__name__)


class Ubus:
    """Interacts with the OpenWrt ubus API."""

    def __init__(
        self,
        host,
        username,
        password,
        session=None,
        timeout=API_DEF_TIMEOUT,
        verify=API_DEF_VERIFY,
    ):
        """Init OpenWrt ubus API."""
        self.host = host
        self.username = username
        self.password = password
        self.session = session if session else requests.Session()
        self.timeout = timeout
        self.verify = verify

        self.debug_api = API_DEF_DEBUG
        self.rpc_id = API_RPC_ID
        self.session_id = None

    def api_call(self, rpc_method, subsystem=None, method=None, params: dict = None):
        """Perform API call."""
        if self.debug_api:
            _LOGGER.debug(
                'api call: rpc_method="%s" subsystem="%s" method="%s" params="%s"',
                rpc_method,
                subsystem,
                method,
                params,
            )

        _params = [self.session_id, subsystem]
        if rpc_method == API_RPC_CALL:
            if method:
                _params.append(method)

            if params:
                _params.append(params)
            else:
                _params.append({})

        data = json.dumps(
            {
                "jsonrpc": API_RPC_VERSION,
                "id": self.rpc_id,
                "method": rpc_method,
                "params": _params,
            }
        )
        if self.debug_api:
            _LOGGER.debug('api call: data="%s"', data)

        self.rpc_id += 1
        try:
            response = requests.post(
                self.host, data=data, timeout=self.timeout, verify=self.verify
            )
        except requests.exceptions.RequestException as req_exc:
            _LOGGER.error("api_call exception: %s", req_exc)
            return None

        if response.status_code != HTTP_STATUS_OK:
            return None

        json_response = response.json()

        if self.debug_api:
            _LOGGER.debug(
                'api call: status="%s" response="%s"',
                response.status_code,
                response.text,
            )

        if API_ERROR in json_response:
            if (
                API_MESSAGE in json_response[API_ERROR]
                and json_response[API_ERROR][API_MESSAGE] == "Access denied"
            ):
                raise PermissionError(json_response[API_ERROR][API_MESSAGE])
            raise ConnectionError(json_response[API_ERROR][API_MESSAGE])

        if rpc_method == API_RPC_CALL:
            try:
                return json_response[API_RESULT][1]
            except IndexError:
                return None
        else:
            return json_response[API_RESULT]

        return None

    def api_debugging(self, debug_api):
        """Enable/Disable API calls debugging."""
        self.debug_api = debug_api
        return self.debug_api

    def https_verify(self, verify):
        """Enable/Disable HTTPS verification."""
        self.verify = verify
        return self.verify

    def connect(self):
        """Connect to OpenWrt ubus API."""
        self.rpc_id = 1
        self.session_id = API_DEF_SESSION_ID

        login = self.api_call(
            API_RPC_CALL,
            API_SUBSYS_SESSION,
            API_METHOD_LOGIN,
            {
                API_PARAM_USERNAME: self.username,
                API_PARAM_PASSWORD: self.password,
            },
        )
        if API_UBUS_RPC_SESSION in login:
            self.session_id = login[API_UBUS_RPC_SESSION]
        else:
            self.session_id = None

        return self.session_id

    def file_read(self, path):
        """Get UCI config."""
        return self.api_call(
            API_RPC_CALL,
            API_SUBSYS_FILE,
            API_METHOD_READ,
            {
                API_PARAM_PATH: path,
            },
        )

    def get_dhcp_method(self, method):
        """Get DHCP method."""
        return self.api_call(API_RPC_CALL, API_SUBSYS_DHCP, method)

    def get_hostapd(self):
        """Get hostapd data."""
        return self.api_call(API_RPC_LIST, API_SUBSYS_HOSTAPD)

    def get_hostapd_clients(self, hostapd):
        """Get hostapd clients."""
        return self.api_call(API_RPC_CALL, hostapd, API_METHOD_GET_CLIENTS)

    def get_uci_config(self, _config, _type):
        """Get UCI config."""
        return self.api_call(
            API_RPC_CALL,
            API_SUBSYS_UCI,
            API_METHOD_GET,
            {
                API_PARAM_CONFIG: _config,
                API_PARAM_TYPE: _type,
            },
        )
