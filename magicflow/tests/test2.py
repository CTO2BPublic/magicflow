approval = {"approval": False}
if not approval['approval']:

    approval.update({
        "workflow_control": {
            "pause": "true",
            "pause_seconds": 30
        },
        "parameters": {"mr_id": 1234,
                       "project_id": 12345
                       }
    })
    print(approval)
