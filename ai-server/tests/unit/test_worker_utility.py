"""
Tests for utility/worker_utility.py

This module tests worker utility functions including dtype conversion.
"""
import pytest


class TestConvertDtypeFromString:
    """Test convert_dtype_from_string function"""

    def test_converts_float32_correctly(self):
        """Should convert 'float32' string to cp.float32"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('float32')
        assert result == cp.float32

    def test_converts_float16_correctly(self):
        """Should convert 'float16' string to cp.float16"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('float16')
        assert result == cp.float16

    def test_converts_int32_correctly(self):
        """Should convert 'int32' string to cp.int32"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('int32')
        assert result == cp.int32

    def test_converts_int16_correctly(self):
        """Should convert 'int16' string to cp.int16"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('int16')
        assert result == cp.int16

    def test_converts_int8_correctly(self):
        """Should convert 'int8' string to cp.int8"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('int8')
        assert result == cp.int8

    def test_handles_uppercase_input(self):
        """Should handle uppercase dtype strings by converting to lowercase"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('FLOAT32')
        assert result == cp.float32

    def test_handles_mixed_case_input(self):
        """Should handle mixed case dtype strings"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        result = convert_dtype_from_string('Float32')
        assert result == cp.float32

        result = convert_dtype_from_string('INT16')
        assert result == cp.int16

    def test_raises_value_error_for_unsupported_dtype(self):
        """Should raise ValueError for unsupported dtype string"""
        from utility.worker_utility import convert_dtype_from_string

        with pytest.raises(ValueError) as exc_info:
            convert_dtype_from_string('float64')

        assert "Unsupported dtype string" in str(exc_info.value)
        assert "float64" in str(exc_info.value)

    def test_raises_value_error_for_invalid_input(self):
        """Should raise ValueError for completely invalid input"""
        from utility.worker_utility import convert_dtype_from_string

        invalid_inputs = ['invalid', 'double', 'uint32', 'string', '']

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError) as exc_info:
                convert_dtype_from_string(invalid_input)

            assert "Unsupported dtype string" in str(exc_info.value)

    def test_returns_correct_dtype_type(self):
        """Should return cupy dtype objects"""
        from utility.worker_utility import convert_dtype_from_string
        import cupy as cp

        # All results should be cupy dtype objects
        dtypes = ['float32', 'float16', 'int32', 'int16', 'int8']

        for dtype_str in dtypes:
            result = convert_dtype_from_string(dtype_str)
            # Check that result is a numpy/cupy dtype
            assert hasattr(result, 'type') or callable(result)
