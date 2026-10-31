def check_edge_input(sdk):
    response = sdk.embed("query: a\U0001f642\0tail")
    expected_tokens = response.prompt_tokens
    assert response.prompt_tokens == expected_tokens
    assert response.prompt_tokens > 0
    assert all_finite_unit_vectors(response.vectors)


def deliver_result(callback, result):
    try:
        callback.on_complete(result)
    except IPCException as error:
        log(error)
