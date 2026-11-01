"""Unfitted estimator preparation only. No dataset loader, fitting or scoring."""
from .pretrain_contracts import FEATURES,seal

LOGISTIC=dict(C=1,solver='lbfgs',max_iter=1000,class_weight=None,random_state=20261030)
FUTURE_REQUIRED={
    'random_forest':{'n_estimators','max_depth','min_samples_leaf','max_features','random_state','n_jobs'},
    'hist_gradient_boosting':{'max_iter','max_leaf_nodes','max_depth','min_samples_leaf','l2_regularization','learning_rate','random_state','early_stopping','validation_fraction'},
}


def catalog():
    return dict(features=list(FEATURES),BUY_SELL='SEPARATE_ESTIMATOR_INSTANCES',decision='p>0.5 FOLLOW; otherwise INVERT',
        logistic=dict(status='FROZEN_NEW_STUDY_SPEC_PREPARED_NOT_AUTHORIZED_TO_FIT',params=LOGISTIC.copy(),scaling='TRAIN_FOLD_ONLY_POPULATION_STANDARD_DEVIATION_ZERO_TO_ONE',missing='NO_IMPUTATION_REPORT_MISSING_FIXED_FOLLOW_NO_FIT_ON_MISSING'),
        **{family:dict(status='PROPOSAL_ONLY_SEPARATE_PREREGISTRATION_REQUIRED',required_explicit_params=sorted(required),scientific_budget=0) for family,required in FUTURE_REQUIRED.items()},
        sequential=dict(status='NOT_IMPLEMENTED_AS_TRAINER_JUSTIFICATION_REQUIRED',requirements=['INDEPENDENT_SEQUENCE_MEMBERSHIP','CAUSAL_WINDOW_AND_PURGE_SPEC','PARAMETER_AND_COMPUTE_BUDGET','JUSTIFICATION_VERSUS_SIMPLE_BASELINES','SEPARATE_PREREGISTRATION_AND_AUTHORIZATION'],scientific_budget=0),
        fits_authorized=0,scoring_authorized=0,current_study_families=['logistic'])


def prepare_unfitted(side,family='logistic',*,proposal_only=False,explicit_params=None):
    if side not in ('BUY','SELL'):raise ValueError('SIDE_MUST_BE_SEPARATE_BUY_OR_SELL')
    if family=='sequential':raise ValueError('SEQUENTIAL_JUSTIFICATION_AND_PROTOCOL_REQUIRED')
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    if family=='logistic':
        from sklearn.linear_model import LogisticRegression
        if explicit_params is not None and explicit_params!=LOGISTIC:raise ValueError('FROZEN_LOGISTIC_PARAMS_CANNOT_CHANGE')
        estimator=Pipeline([('scale',StandardScaler()),('model',LogisticRegression(**LOGISTIC))])
        params=LOGISTIC.copy();permitted_family=True
    elif family in FUTURE_REQUIRED:
        if not proposal_only:raise ValueError('FAMILY_OUTSIDE_FROZEN_STUDY_PROTOCOL')
        if not isinstance(explicit_params,dict) or set(explicit_params)!=FUTURE_REQUIRED[family]:raise ValueError('COMPLETE_FUTURE_SPEC_REQUIRED_NO_SEARCH_DEFAULTS')
        params=dict(explicit_params);permitted_family=False
        if type(params['random_state']) is not int:raise ValueError('EXPLICIT_FIXED_SEED_REQUIRED')
        if family=='random_forest':
            from sklearn.ensemble import RandomForestClassifier
            if params['n_jobs']!=1:raise ValueError('PC_A_SINGLE_JOB_REQUIRED')
            estimator=RandomForestClassifier(**params)
        else:
            from sklearn.ensemble import HistGradientBoostingClassifier
            if params['early_stopping'] is not False or params['validation_fraction'] is not None:raise ValueError('NO_AUTOMATIC_RANDOM_VALIDATION_SPLIT')
            estimator=HistGradientBoostingClassifier(**params)
    else:raise ValueError('UNKNOWN_MODEL_FAMILY')
    import sklearn
    metadata=dict(side=side,family=family,params=params,feature_order=list(FEATURES),sklearn_version=sklearn.__version__,current_protocol_family=permitted_family,proposal_only=not permitted_family,training_authorized=False,scoring_authorized=False,fit_calls=0)
    return estimator,dict(metadata,spec_sha256=seal(metadata))
