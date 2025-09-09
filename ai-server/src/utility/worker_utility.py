import cupy as cp


def convert_dtype_from_string(dtype_str):
    dtype_str = dtype_str.lower()
    if dtype_str == 'float32':
        return cp.float32
    elif dtype_str == 'float16':
        return cp.float16
    elif dtype_str == 'int32':
        return cp.int32
    elif dtype_str == 'int16':
        return cp.int16
    elif dtype_str == 'int8':
        return cp.int8
    else:
        raise ValueError(f"Unsupported dtype string: {dtype_str}")