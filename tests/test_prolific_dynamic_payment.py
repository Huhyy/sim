from unittest.mock import patch

from sim_app.prolific.bonuses import complete_with_dynamic_payment, dynamic_reward_percentage


def test_dynamic_reward_percentage_includes_base_reward_and_bonus():
    assert dynamic_reward_percentage(5, 1) == 120
    assert dynamic_reward_percentage(5, 2) == 140
    assert dynamic_reward_percentage(5, 3) == 160


def test_dynamic_completion_uses_submission_id_and_completion_data():
    with patch("sim_app.prolific.bonuses._request", return_value={"status": "AWAITING REVIEW"}) as request:
        result = complete_with_dynamic_payment("submission-1", "CFQP1FU2", 140, "Performance reward")

    assert result == {"status": "AWAITING REVIEW"}
    request.assert_called_once_with(
        "POST",
        "/submissions/submission-1/transition/",
        {
            "action": "COMPLETE",
            "completion_code": "CFQP1FU2",
            "completion_code_data": {
                "percentage_of_reward": 140.0,
                "message_to_participant": "Performance reward",
            },
        },
    )
