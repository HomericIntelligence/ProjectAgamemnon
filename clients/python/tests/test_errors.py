"""Tests for the agamemnon_client error hierarchy."""

import pytest

from agamemnon_client.errors import (
    AgamemnonAPIError,
    AgamemnonConnectionError,
    AgamemnonError,
)


class TestAgamemnonError:
    def test_is_exception(self) -> None:
        err = AgamemnonError("base error")
        assert isinstance(err, Exception)

    def test_message(self) -> None:
        err = AgamemnonError("something went wrong")
        assert str(err) == "something went wrong"


class TestAgamemnonConnectionError:
    def test_is_agamemnon_error(self) -> None:
        err = AgamemnonConnectionError("cannot connect")
        assert isinstance(err, AgamemnonError)

    def test_message(self) -> None:
        err = AgamemnonConnectionError("connection refused")
        assert str(err) == "connection refused"

    def test_raised_as_agamemnon_error(self) -> None:
        with pytest.raises(AgamemnonError):
            raise AgamemnonConnectionError("timeout")


class TestAgamemnonAPIError:
    def test_is_agamemnon_error(self) -> None:
        err = AgamemnonAPIError(404, "not found")
        assert isinstance(err, AgamemnonError)

    def test_status_code_stored(self) -> None:
        err = AgamemnonAPIError(500, "internal server error")
        assert err.status_code == 500

    def test_message_stored(self) -> None:
        err = AgamemnonAPIError(400, "bad request")
        assert err.message == "bad request"

    def test_str_includes_status_and_message(self) -> None:
        err = AgamemnonAPIError(403, "forbidden")
        assert "403" in str(err)
        assert "forbidden" in str(err)

    @pytest.mark.parametrize(
        "status_code,message",
        [
            (400, "invalid JSON"),
            (404, "agent not found"),
            (500, "internal server error"),
        ],
    )
    def test_various_codes(self, status_code: int, message: str) -> None:
        err = AgamemnonAPIError(status_code, message)
        assert err.status_code == status_code
        assert err.message == message
        assert str(status_code) in str(err)
        assert message in str(err)

    def test_raised_as_agamemnon_error(self) -> None:
        with pytest.raises(AgamemnonError):
            raise AgamemnonAPIError(503, "service unavailable")
