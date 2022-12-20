# stdlib
from typing import Any

# third party
import numpy as np
from jax.numpy import DeviceArray

# syft absolute
import pytest

import syft as sy
from syft.core.adp.data_subject_ledger import DataSubjectLedger
from syft.core.adp.data_subject_ledger import convert_constants_to_indices
from syft.core.adp.ledger_store import DictLedgerStore


class UserBudget:
    def __init__(self, value: int) -> None:
        self.budget = value
        self.current_spend = 0


user_budget = UserBudget(150)


def get_budget_for_user(*args: Any, **kwargs: Any) -> int:
    return user_budget.budget


def deduct_epsilon_for_user(
    verify_key: Any, old_budget: int, epsilon_spend: int
) -> None:
    user_budget.budget = old_budget - epsilon_spend
    user_budget.current_spend = epsilon_spend


@pytest.fixture
def dataset() -> np.ndarray:
    return np.random.randint(low=1, high=8, size=(5, 5))


def test_privacy_budget_spend_on_publish():
    fred_nums = np.array([25, 35, 21])
    sally_nums = np.array([8, 11, 10])

    fred_tensor = sy.Tensor(fred_nums).annotate_with_dp_metadata(
        lower_bound=0, upper_bound=122, data_subject="fred"
    )

    sally_tensor = sy.Tensor(sally_nums).annotate_with_dp_metadata(
        lower_bound=0, upper_bound=122, data_subject="sally"
    )

    result = fred_tensor + sally_tensor

    ledger_store = DictLedgerStore()

    user_key = b"1231"

    ledger = DataSubjectLedger.get_or_create(store=ledger_store, user_key=user_key)

    pub_result_sally = sally_tensor.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=50,
        private=True,
    )

    assert pub_result_sally is not None

    eps_spend_for_sally = user_budget.current_spend

    pub_result_fred = sally_tensor.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=50,
        private=True,
    )

    assert pub_result_fred is not None

    eps_spend_for_fred = user_budget.current_spend

    # Epsilon spend for sally should be equal to fred
    # since they impact the same of values in the data independently
    assert eps_spend_for_sally == eps_spend_for_fred

    pub_result_comb = result.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=50,
        private=True,
    )

    assert pub_result_comb is not None

    # TODO: Need to confirm if this ratio will always be less than 1
    # assert (eps_spend_for_fred + eps_spend_for_sally) / combined_eps_spend < 1

    # This should only filter out values of fred or sally
    pub_result_comb2 = result.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=50,
        private=True,
    )
    assert pub_result_comb2 is not None
    # assert user_budget.current_spend == 0.0
    # TODO: Do we need caching?

    mul_tensor = (fred_tensor + sally_tensor) * 2

    print(mul_tensor.child.lipschitz_bound)
    # This should only filter out values of fred or sally
    pub_result_comb4 = mul_tensor.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=50,
        private=True,
    )
    assert pub_result_comb4 is not None


def test_publish_phi_tensor(dataset: np.ndarray) -> None:
    """ Test that you can still publish PhiTensors"""
    tensor = sy.Tensor(dataset).annotate_with_dp_metadata(lower_bound=0, upper_bound=10, data_subject="Mr. Potato")
    ledger_store = DictLedgerStore()
    user_key = b"6874"
    ledger = DataSubjectLedger.get_or_create(store=ledger_store, user_key=user_key)
    result = tensor.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=2,
        private=True,
    )
    assert result is not None
    assert isinstance(result, (np.ndarray, DeviceArray))
    assert result.shape == dataset.shape
    print(ledger._rdp_constants)
    assert ledger._rdp_constants is not None
    assert user_budget.current_spend > 0


def test_publish_new_subjects(dataset: np.ndarray) -> None:
    """Test that the ledger updates correctly when data of new data subjects are published"""
    tensor1 = sy.Tensor(dataset).annotate_with_dp_metadata(
        lower_bound=0, upper_bound=10, data_subject="Mr Potato"
    )

    tensor2 = sy.Tensor(dataset).annotate_with_dp_metadata(
        lower_bound=0, upper_bound=10, data_subject="Mrs Potato"
    )

    ledger_store = DictLedgerStore()
    user_key = b"1642"
    ledger = DataSubjectLedger.get_or_create(store=ledger_store, user_key=user_key)

    result1 = tensor1.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=5,
        private=True,
    )

    assert result1 is not None
    assert isinstance(result1, (np.ndarray, DeviceArray))
    assert result1.shape == dataset.shape
    assert len(ledger._rdp_constants) == 1
    eps_spend_query1 = user_budget.current_spend

    result2 = tensor2.publish(
        get_budget_for_user=get_budget_for_user,
        deduct_epsilon_for_user=deduct_epsilon_for_user,
        ledger=ledger,
        sigma=5,
        private=True,
    )

    assert result2 is not None
    assert isinstance(result2, (np.ndarray, DeviceArray))
    assert result2.shape == dataset.shape
    assert len(ledger._rdp_constants) == 2
    eps_spend_query2 = user_budget.current_spend

    assert eps_spend_query2 < eps_spend_query1


def test_publish_unchanged_pb() -> None:
    """ When publishing two queries with different data subjects but identical data and sigma, no PB should be spent."""
    pass


def test_publish_existing_subjects() -> None:
    """Test the ledger is updated correctly when existing data subjects have more data published"""
    pass


def test_publish_sigma_affects_pb() -> None:
    """ Test that increasing sigma decreases the privacy budget spent. """
    pass
