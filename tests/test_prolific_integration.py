import json
from unittest.mock import MagicMock, patch

import pytest

from sim_app.application.errors import ProlificLaunchError
from sim_app.prolific.bonuses import create_bonus_payment
from sim_app.prolific.submissions import verify_prolific_submission


def _response(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_submission_verification_matches_all_generated_launch_identifiers():
    payload = {"id": "submission-1", "participant": "participant-1", "study_id": "study-1", "status": "ACTIVE"}
    with (
        patch("sim_app.prolific.submissions._get_secret", side_effect=lambda name: {
            "PROLIFIC_API_TOKEN": "api-token",
            "PUBLIC_ORIGIN": "https://simulator.example",
        }.get(name)),
        patch(
            "sim_app.prolific.submissions.urlopen",
            side_effect=[_response(payload), _response({"external_study_url": "https://simulator.example/?PROLIFIC_PID=x"})],
        ) as urlopen,
    ):
        result = verify_prolific_submission(
            submission_id="submission-1",
            participant_id="participant-1",
            study_id="study-1",
        )

    assert result == payload
    assert urlopen.call_count == 2
    request = urlopen.call_args_list[0].args[0]
    assert request.full_url.endswith("/submissions/submission-1/")
    assert request.get_method() == "GET"
    assert request.get_header("Authorization") == "Token api-token"


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", "other"), ("participant", "other"), ("study_id", "other")],
)
def test_submission_verification_rejects_each_mismatched_identifier(field, value):
    payload = {"id": "submission-1", "participant": "participant-1", "study_id": "study-1"}
    payload[field] = value
    with (
        patch("sim_app.prolific.submissions._get_secret", side_effect=lambda name: {
            "PROLIFIC_API_TOKEN": "api-token",
            "PUBLIC_ORIGIN": "https://simulator.example",
        }.get(name)),
        patch("sim_app.prolific.submissions.urlopen", return_value=_response(payload)),
        pytest.raises(ProlificLaunchError),
    ):
        verify_prolific_submission(
            submission_id="submission-1",
            participant_id="participant-1",
            study_id="study-1",
        )


def test_submission_verification_fails_closed_without_api_token():
    with patch("sim_app.prolific.submissions._get_secret", return_value=None), pytest.raises(ProlificLaunchError):
        verify_prolific_submission(submission_id="submission-1", participant_id="participant-1", study_id="study-1")


def test_submission_verification_rejects_a_real_tuple_from_an_unrelated_study_destination():
    submission = {"id": "submission-1", "participant": "participant-1", "study_id": "study-1"}
    with (
        patch("sim_app.prolific.submissions._get_secret", side_effect=lambda name: {
            "PROLIFIC_API_TOKEN": "api-token",
            "PUBLIC_ORIGIN": "https://simulator.example",
        }.get(name)),
        patch(
            "sim_app.prolific.submissions.urlopen",
            side_effect=[_response(submission), _response({"external_study_url": "https://another-study.example/"})],
        ),
        pytest.raises(ProlificLaunchError),
    ):
        verify_prolific_submission(
            submission_id="submission-1",
            participant_id="participant-1",
            study_id="study-1",
        )


def test_bonus_creation_uses_reviewable_batch_endpoint_and_never_pay_endpoint():
    with patch("sim_app.prolific.bonuses._request", return_value={"id": "bonus-1"}) as request:
        result = create_bonus_payment("study-1", "submission-1", 2)

    assert result == {"id": "bonus-1"}
    request.assert_called_once_with(
        "POST",
        "/submissions/bonus-payments/",
        {"study_id": "study-1", "csv_bonuses": "submission-1,2.00\n"},
    )
    assert "/pay/" not in request.call_args.args[1]


def test_bonus_api_request_identifies_the_same_origin_web_integration():
    response = _response({})
    with (
        patch("sim_app.prolific.bonuses._get_secret", side_effect=lambda name: {
            "PROLIFIC_API_TOKEN": "api-token",
            "PROLIFIC_INTEGRATION_URL": "https://simulator.example/",
        }.get(name)),
        patch("sim_app.prolific.bonuses.urlopen", return_value=response) as urlopen,
    ):
        create_bonus_payment("study-1", "submission-1", 0)

    request = urlopen.call_args.args[0]
    assert request.get_header("Authorization") == "Token api-token"
    assert request.get_header("Accept") == "application/json"
    assert request.get_header("Referer") == "https://simulator.example/"
    assert request.get_header("User-agent") == "ScenariuCredit/1.0 (Prolific API integration)"
