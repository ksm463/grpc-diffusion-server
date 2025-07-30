from fastapi import Request, HTTPException, status

def get_manager_config(request: Request):
    try:
        manager_config = request.app.state.manager_config
        if manager_config is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Config not initialized")
        return manager_config
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Config attribute not found in app state")

def get_server_config(request: Request):
    try:
        server_config = request.app.state.server_config
        if server_config is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="gRPC Config not initialized")
        return server_config
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="gRPCConfig attribute not found in app state")

def get_logger(request: Request):
    try:
        logger = request.app.state.logger
        if logger is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logger not initialized")
        return logger
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logger attribute not found in app state")
