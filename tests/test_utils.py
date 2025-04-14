import pytest
from core.utils import haversine_distance, is_valid_coordinates


def test_is_valid_coordinates_valid():
    assert is_valid_coordinates(0, 0) is True
    assert is_valid_coordinates(90, 180) is True
    assert is_valid_coordinates(-90, -180) is True
    assert is_valid_coordinates(32, 34.78) is True


def test_is_valid_coordinates_invalid():
    assert is_valid_coordinates(95, 0) is False
    assert is_valid_coordinates(-95, 0) is False
    assert is_valid_coordinates(0, 200) is False
    assert is_valid_coordinates(0, -200) is False


def test_is_valid_coordinates_non_numeric():
    assert is_valid_coordinates("abc", 34.78) is False
    assert is_valid_coordinates(32.08, "xyz") is False
    assert is_valid_coordinates(None, 34.78) is False
    assert is_valid_coordinates(32.08, None) is False
    assert is_valid_coordinates([32.08], 34.78) is False


def test_haversine_distance_zero():
    d = haversine_distance(0, 0, 0, 0)
    assert d == 0.0


def test_haversine_distance_tel_aviv_to_jerusalem():

    d = haversine_distance(32.0853, 34.7818, 31.7683, 35.2137)
    assert 50 < d < 70


def test_haversine_distance_half_globe():
    d = haversine_distance(0, 0, 0, 180)
    assert 20000 < d < 20040
