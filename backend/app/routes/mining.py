from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.database.connection import get_db
from app.database.repositories import MiningRepository
from app.deps import get_current_user_id
from app.services.apriori_service import (
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_SUPPORT,
    run_apriori,
)
from app.services.kmeans_service import K_DEFAULT, run_kmeans
from app.services.naive_bayes_service import run_naive_bayes

router = APIRouter(prefix="/api/mining", tags=["mining"])


class KMeansInput(BaseModel):
    k: int = K_DEFAULT


class AprioriInput(BaseModel):
    min_support: float = DEFAULT_MIN_SUPPORT
    min_confidence: float = DEFAULT_MIN_CONFIDENCE
    min_lift: float | None = None


@router.post("/kmeans")
def kmeans(
    body: KMeansInput | None = None,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    k = (body or KMeansInput()).k
    result = run_kmeans(db, user_id, k)
    run_id = MiningRepository.create_run(
        db,
        user_id,
        "kmeans",
        parameters={"k": result["k"]},
        metrics={
            "silhouette_score": result["silhouette_score"],
            "movie_count": result["movie_count"],
            "clusters": len(result["profiles"]),
        },
    )
    MiningRepository.save_kmeans(db, run_id, result["assignments"], result["profiles"])
    return {"run_id": run_id, **result}


@router.post("/apriori")
def apriori(
    body: AprioriInput | None = None,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    params = body or AprioriInput()
    result = run_apriori(
        db,
        min_support=params.min_support,
        min_confidence=params.min_confidence,
        min_lift=params.min_lift,
    )
    run_id = MiningRepository.create_run(
        db,
        user_id,
        "apriori",
        parameters={
            "min_support": result["min_support"],
            "min_confidence": result["min_confidence"],
            "min_lift": result["min_lift"],
        },
        metrics={
            "transaction_count": result["transaction_count"],
            "frequent_itemset_count": result["frequent_itemset_count"],
            "rule_count": len(result["rules"]),
        },
    )
    if result["rules"]:
        MiningRepository.save_rules(db, run_id, result["rules"])
    return {"run_id": run_id, **result}


@router.post("/naive-bayes")
def naive_bayes(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    result = run_naive_bayes(db, user_id)
    run_id = MiningRepository.create_run(
        db,
        user_id,
        "naive_bayes",
        parameters={"test_size": 0.25, "min_positives": 4},
        metrics={
            "trained_movies": result["trained_movies"],
            "modelled_genres": result["modelled_genres"],
            "mean_accuracy": round(
                sum(m["accuracy"] for m in result["metrics"]) / len(result["metrics"]), 4
            )
            if result["metrics"]
            else None,
        },
    )
    MiningRepository.save_naive_bayes(db, run_id, result["probabilities"])
    return {"run_id": run_id, **result}


@router.get("/runs")
def runs(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    return {"runs": MiningRepository.list_runs(db, user_id)}
