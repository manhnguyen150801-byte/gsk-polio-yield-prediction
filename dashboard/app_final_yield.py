import streamlit as st
import pandas as pd
import numpy as np
import joblib
from pathlib import Path




# ============================================================
# Page configuration
# ============================================================
st.set_page_config(
    page_title="AI Yield Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)




# ============================================================
# Paths
# ============================================================
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"


DATA_PATHS = {
    "IP1": BASE_DIR.parent / "data" / "basetable" / "ip1_basetable_v5.parquet",
    "IP3": BASE_DIR.parent / "data" / "basetable" / "ip3_basetable_v5.parquet",
}


MODEL_DIR = BASE_DIR.parent / "models"




# ============================================================
# App constants
# ============================================================
STAGES = [
    "Clarification",
    "Ultrafiltration",
    "PG",
    "PSV",
    "Global Yield",
]


MODEL_OPTIONS = [
    "Linear Regression",
    "RandomForest",
    "HGB",
]


MODEL_INTERNAL = {
    "Linear Regression": "OLS",
    "RandomForest": "RandomForest",
    "HGB": "HGB",
}


MODEL_DISPLAY = {
    "OLS": "Linear Regression",
    "RandomForest": "RandomForest",
    "HGB": "HGB",
}


BEST_MODEL_BY_IP_STAGE = {
    ("IP1", "Clarification"): "Linear Regression",
    ("IP1", "Ultrafiltration"): "RandomForest",
    ("IP1", "PG"): "HGB",
    ("IP1", "PSV"): "HGB",
    ("IP1", "Global Yield"): "HGB",


    ("IP3", "Clarification"): "Linear Regression",
    ("IP3", "Ultrafiltration"): "HGB",
    ("IP3", "PG"): "HGB",
    ("IP3", "PSV"): "HGB",
    ("IP3", "Global Yield"): "HGB",
}


MODEL_PATHS = {
    ("IP1", "Clarification", "Linear Regression"): [MODEL_DIR / "IP1_clarif_model.pkl"],
    ("IP1", "Ultrafiltration", "RandomForest"): [MODEL_DIR / "IP1_uf_model.pkl"],
    ("IP1", "PG", "HGB"): [MODEL_DIR / "IP1_pg_model.pkl"],
    ("IP1", "PSV", "HGB"): [MODEL_DIR / "IP1_psv_model.pkl"],


    ("IP1", "Global Yield", "Linear Regression"): [MODEL_DIR / "IP1_ols_global_model.pkl"],
    ("IP1", "Global Yield", "RandomForest"): [MODEL_DIR / "IP1_rf_global_model.pkl"],
    ("IP1", "Global Yield", "HGB"): [MODEL_DIR / "IP1_hgb_global_model.pkl"],


    ("IP3", "Clarification", "Linear Regression"): [MODEL_DIR / "IP3_clarif_model.pkl"],
    ("IP3", "Ultrafiltration", "HGB"): [MODEL_DIR / "IP3_uf_model.pkl"],
    ("IP3", "PG", "HGB"): [MODEL_DIR / "IP3_pg_model.pkl"],
    ("IP3", "PSV", "HGB"): [MODEL_DIR / "IP3_psv_model.pkl"],


    ("IP3", "Global Yield", "Linear Regression"): [MODEL_DIR / "IP3_ols_global_model.pkl"],
    ("IP3", "Global Yield", "RandomForest"): [MODEL_DIR / "IP3_rf_global_model.pkl"],
    ("IP3", "Global Yield", "HGB"): [MODEL_DIR / "IP3_hgb_global_model.pkl"],
}




# ============================================================
# SHAP-based feature lists
# ============================================================
# These are fixed feature lists taken from the blue SHAP bar charts in the notebook.
# The app does not recalculate SHAP; it uses these lists to decide which features to display.
# If a listed feature is not available in the model bundle, the app falls back to model features
# so the prediction page can still run safely.
SHAP_FEATURES = {
    ("IP1", "Clarification", "Linear Regression"): [
        "clarif_Clarif 1 - Flow 340L (L/min)",
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
    ],
    ("IP1", "Ultrafiltration", "RandomForest"): [
        "UF_UF - Ag total",
        "UF_003 UF - Ag content Elisa [DU/ml]",
        "UF_PG - Volume injected ml [ml]",
    ],
    ("IP1", "PG", "HGB"): [
        "PG_PG - Ag total",
        "PG_DEAE - Volume injected ml [ml]",
        "pg_sub_pc4",
        "pg_sensor_RunCalc_UV_ForIntegral_v2_std",
        "pg_sensor_MT_I2_OUT_std",
        "pg_sub_pc2",
        "PG_004 PG - Ag content Elisa [DU/ml]",
        "pg_sensor_RunCalc_UV_ForIntegral_v2_max",
        "pg_sensor_UV Elution_max",
        "pg_sensor_PI_A2_max",
    ],
    ("IP1", "PSV", "HGB"): [
        "PSV_PSV - Ag total",
        "PSV_020 PSV - Protein/dose (Lowry) [µg of pr",
        "PSV_019 PSV - Protein by lowry [µg/ml]",
        "PSV_PSV - Volume ml [ml]",
        "PSV_PSV - Filtration time [Minute]",
        "PSV_005 PSV - Ag content Elisa [DU/ml]",
        "PSV_PSV - Prot total [mg]",
        "PSV_021 PSV - BSA content by Elisa [ng/ml]",
    ],
    ("IP1", "Global Yield", "HGB"): [
        "PSV_PSV - Ag total",
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
        "PSV_005 PSV - Ag content Elisa [DU/ml]",
        "pg_sensor_PIC_A1_mean",
        "PSV_020 PSV - Protein/dose (Lowry) [µg of pr",
        "PG_004 PG - Ag content Elisa [DU/ml]",
        "deae_child2_xto_prompt__12_1",
        "pg_child2_xto_prompt__1_1",
        "clarif_D5 8h-Cells count",
        "pg_sensor_RunCalc_UV_DuringHarvest_max",
    ],


    ("IP3", "Clarification", "Linear Regression"): [
        "clarif_Duration cells pool transfer [Minute]",
        "eng4_clarif_d0_x_d5",
        "clarif_D5 8h-Cells count",
        "eng4_clarif_ag_x_duration",
        "clarif_D0-Cells count",
        "eng4_clarif_protein_x_duration",
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
        "eng4_clarif_cells_x_duration",
        "clarif_014 Protein Lowry virus cult [µg/ml]",
    ],
    ("IP3", "Ultrafiltration", "HGB"): [
        "eng4_uf_elisa_x_volume",
        "eng4_uf_ag_elisa_x_total",
        "UF_003 UF - Ag content Elisa [DU/ml]",
        "eng4_uf_ag_x_volume",
        "UF_UF - Ag total",
        "UF_UF - Volume UFR ml [ml]",
    ],
    ("IP3", "PG", "HGB"): [
        "PG_004 PG - Ag content Elisa [DU/ml]",
        "eng4_pg_xv_x_uv_harvest",
        "eng4_pg_ag_x_packing_s1",
        "eng4_pg_ag_x_accumulated_vol",
        "eng4_pg_ti_a1_x_ti_a2",
        "eng4_pg_ag_x_packing_s2",
        "PG_PG - Ag total",
    ],
    ("IP3", "PSV", "HGB"): [
        "eng4_psv_ag_x_volume",
        "PSV_005 PSV - Ag content Elisa [DU/ml]",
        "PSV_PSV - Prot total [mg]",
        "eng4_psv_ag_x_elisa",
        "PSV_PSV - Filtration time [Minute]",
        "PSV_PSV - Volume ml [ml]",
        "PSV_PSV - Ag total",
    ],
    ("IP3", "Global Yield", "HGB"): [
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
        "eng4_psv_ag_x_volume",
        "PSV_PSV - Ag total",
        "PSV_005 PSV - Ag content Elisa [DU/ml]",
        "eng4_psv_ag_x_elisa",
        "pg_child2_xto_cip_201__5_1",
        "deae_sub_pc5",
        "deae_child2_xto_alarm_201__8_1",
        "pg_sensor_RunCalc_UV_DuringHarvest_max",
        "pg_sensor_MT_I2_OUT_std",
    ],
}




# ============================================================
# Model performance results
# ============================================================
# Column order in the app: NRMSE, RMSE, R².
# "Best" is marked by lowest NRMSE for each IP/stage row.
PERFORMANCE_RESULTS = {
    "IP1": {
        "Clarification": {
            "Linear Regression": {"NRMSE": 0.0993, "RMSE": 6.7600, "R²": 0.0255},
            "RandomForest": {"NRMSE": 0.1003, "RMSE": 6.8264, "R²": 0.0062},
            "HGB": {"NRMSE": 0.0995, "RMSE": 6.7764, "R²": 0.0207},
        },
        "Ultrafiltration": {
            "Linear Regression": {"NRMSE": 0.1040, "RMSE": 9.6100, "R²": -0.0323},
            "RandomForest": {"NRMSE": 0.0971, "RMSE": 8.9627, "R²": 0.1020},
            "HGB": {"NRMSE": 0.0978, "RMSE": 9.0323, "R²": 0.0880},
        },
        "PG": {
            "Linear Regression": {"NRMSE": 0.0700, "RMSE": 5.7890, "R²": 0.0405},
            "RandomForest": {"NRMSE": 0.0669, "RMSE": 5.5386, "R²": 0.1216},
            "HGB": {"NRMSE": 0.0647, "RMSE": 5.3621, "R²": 0.1767},
        },
        "PSV": {
            "Linear Regression": {"NRMSE": 0.0810, "RMSE": 5.5900, "R²": 0.3548},
            "RandomForest": {"NRMSE": 0.0822, "RMSE": 5.6959, "R²": 0.3300},
            "HGB": {"NRMSE": 0.0731, "RMSE": 5.0655, "R²": 0.4701},
        },
        "Global Yield": {
            "Linear Regression": {"NRMSE": 0.0710, "RMSE": 2.5406, "R²": 0.3528},
            "RandomForest": {"NRMSE": 0.0705, "RMSE": 2.5078, "R²": 0.3693},
            "HGB": {"NRMSE": 0.0419, "RMSE": 1.4891, "R²": 0.7776},
        },
    },
    "IP3": {
        "Clarification": {
            "Linear Regression": {"NRMSE": 0.1090, "RMSE": 6.9127, "R²": 0.0497},
            "RandomForest": {"NRMSE": 0.1057, "RMSE": 6.6986, "R²": 0.1077},
            "HGB": {"NRMSE": 0.1030, "RMSE": 6.5336, "R²": 0.1511},
        },
        "Ultrafiltration": {
            "Linear Regression": {"NRMSE": 0.1090, "RMSE": 10.2500, "R²": 0.1766},
            "RandomForest": {"NRMSE": 0.1087, "RMSE": 10.1754, "R²": 0.1885},
            "HGB": {"NRMSE": 0.1049, "RMSE": 9.8222, "R²": 0.2439},
        },
        "PG": {
            "Linear Regression": {"NRMSE": 0.0640, "RMSE": 4.9440, "R²": 0.1312},
            "RandomForest": {"NRMSE": 0.0657, "RMSE": 5.0580, "R²": 0.0908},
            "HGB": {"NRMSE": 0.0625, "RMSE": 4.8146, "R²": 0.1762},
        },
        "PSV": {
            "Linear Regression": {"NRMSE": 0.0930, "RMSE": 6.8500, "R²": -0.0560},
            "RandomForest": {"NRMSE": 0.0899, "RMSE": 6.6060, "R²": 0.0179},
            "HGB": {"NRMSE": 0.0881, "RMSE": 6.4785, "R²": 0.0554},
        },
        "Global Yield": {
            "Linear Regression": {"NRMSE": 0.3160, "RMSE": 10.4390, "R²": -17.6792},
            "RandomForest": {"NRMSE": 0.0624, "RMSE": 2.0644, "R²": 0.2696},
            "HGB": {"NRMSE": 0.0424, "RMSE": 1.4007, "R²": 0.6637},
        },
    },
}




# ============================================================
# Custom CSS
# ============================================================
st.markdown(
    """
    <style>
    :root {
        --gsk-orange: #F36F21;
        --gsk-dark-orange: #C94F10;
        --gsk-soft-orange: #FFF1E7;
        --gsk-text: #262A33;
        --gsk-muted: #5F6673;
        --gsk-border: #F1C2A2;
    }


    .stApp {
        background: linear-gradient(180deg, #FFFFFF 0%, #FFF8F2 100%);
    }


    .block-container {
        padding-top: 2.4rem;
        padding-bottom: 3rem;
        max-width: 1230px;
    }


    h1 {
        color: var(--gsk-text);
        font-size: 3rem !important;
        line-height: 1.1 !important;
        letter-spacing: -0.04em;
    }


    h2 {
        color: var(--gsk-text);
        font-size: 2rem !important;
        letter-spacing: -0.03em;
    }


    h3 {
        color: var(--gsk-text);
        letter-spacing: -0.02em;
    }


    p, li, div {
        font-size: 1.04rem;
    }


    p {
        color: #374151;
        line-height: 1.75;
    }


    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2B211D 0%, #16110F 100%);
        border-right: 5px solid var(--gsk-orange);
    }


    [data-testid="stSidebar"] * {
        color: #FFFFFF;
    }


    [data-testid="stSidebar"] .stRadio label {
        font-weight: 650;
    }


    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.22);
    }


    div[data-testid="stButton"] > button {
        background-color: var(--gsk-orange);
        color: white;
        border: 1px solid var(--gsk-orange);
        border-radius: 10px;
        font-weight: 800;
        padding: 0.7rem 1rem;
    }


    div[data-testid="stButton"] > button:hover {
        background-color: var(--gsk-dark-orange);
        border: 1px solid var(--gsk-dark-orange);
        color: white;
    }


    .thin-section-line {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, var(--gsk-orange), rgba(243,111,33,0.22), transparent);
        margin: 2.2rem 0 1.7rem 0;
    }


    .logo-area {
        padding-bottom: 1rem;
        margin-bottom: 1.4rem;
        border-bottom: 1px solid #F1D4C0;
    }


    .intro-label {
        color: var(--gsk-orange);
        font-weight: 850;
        text-transform: uppercase;
        font-size: 0.82rem;
        letter-spacing: 0.12em;
        margin-bottom: 0.75rem;
        line-height: 1.6;
    }


    .section-box {
        background-color: #FFFFFF;
        padding: 1.45rem 1.55rem;
        border: 1px solid #F1D4C0;
        box-shadow: 0px 8px 24px rgba(31, 41, 55, 0.045);
        margin-bottom: 1rem;
    }


    .highlight-box {
        background: linear-gradient(135deg, #FFF0E5 0%, #FFFFFF 78%);
        padding: 1.5rem 1.6rem;
        border: 1px solid #F5B98B;
        border-left: 8px solid var(--gsk-orange);
        box-shadow: 0px 12px 28px rgba(243, 111, 33, 0.10);
        margin-bottom: 1rem;
    }


    .metric-card {
        background-color: #FFFFFF;
        padding: 1.25rem 1.3rem;
        border: 1px solid #F1D4C0;
        border-top: 6px solid var(--gsk-orange);
        box-shadow: 0px 8px 24px rgba(31, 41, 55, 0.05);
        height: 100%;
    }


    .metric-label {
        color: var(--gsk-muted);
        font-size: 0.98rem;
        margin-bottom: 0.35rem;
    }


    .metric-value {
        color: #111827;
        font-size: 1.9rem;
        font-weight: 850;
        line-height: 1.2;
    }


    .metric-note {
        color: var(--gsk-muted);
        font-size: 0.98rem;
        margin-top: 0.45rem;
        line-height: 1.55;
    }


    .small-muted {
        color: var(--gsk-muted);
        font-size: 1rem;
        line-height: 1.6;
    }


    .subtle-note {
        background-color: #FFF7F0;
        border-left: 5px solid var(--gsk-orange);
        padding: 0.95rem 1.05rem;
        color: #6B3B20;
        font-size: 1rem;
        margin-top: 0.8rem;
        line-height: 1.6;
    }


    .fixed-model-box {
        background-color: #FFFFFF;
        border: 1px solid #F1D4C0;
        border-left: 6px solid var(--gsk-orange);
        padding: 1rem 1.1rem;
        margin-top: 0.4rem;
        box-shadow: 0px 6px 18px rgba(31, 41, 55, 0.045);
    }


    [data-testid="stImageCaption"] {
        font-size: 1.04rem !important;
        color: #5F6673 !important;
        text-align: center;
        line-height: 1.6 !important;
    }


    [data-testid="stImageCaption"] p {
        font-size: 1.04rem !important;
        color: #5F6673 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)




# ============================================================
# Utility functions
# ============================================================
def horizontal_line():
    st.markdown('<hr class="thin-section-line">', unsafe_allow_html=True)




def normalize_feature_name(name):
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("—", "")
        .replace(":", "")
        .replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
    )




def find_existing_path(paths):
    for path in paths:
        if path.exists():
            return path
    return None




def show_logo_area():
    ieseg_path = ASSETS_DIR / "IÉSEG_logo_Hackathon.png"
    gsk_path = ASSETS_DIR / "gsk.png"


    st.markdown('<div class="logo-area">', unsafe_allow_html=True)


    logo_col, text_col = st.columns([1, 4])


    with logo_col:
        if ieseg_path.exists():
            st.image(str(ieseg_path), width=115)
        else:
            st.markdown("IÉSEG")


        if gsk_path.exists():
            st.image(str(gsk_path), width=112)
        else:
            st.markdown("GSK")


    with text_col:
        st.markdown(
            """
            <div class="intro-label">Hackathon Decision-Support Prototype</div>
            <p style="margin-bottom:0;">
                A Streamlit interface for batch-level yield prediction and model result communication.
            </p>
            """,
            unsafe_allow_html=True
        )


    st.markdown('</div>', unsafe_allow_html=True)




def show_optional_image(file_name, caption):
    image_path = ASSETS_DIR / file_name


    if image_path.exists():
        st.image(str(image_path), caption=caption, use_container_width=True)
    else:
        st.info(f"Visual file not found: {file_name}")


    horizontal_line()




# ============================================================
# Feature engineering
# ============================================================
def safe_product(df, col_a, col_b):
    if col_a in df.columns and col_b in df.columns:
        return df[col_a] * df[col_b]
    return np.nan




def safe_ratio(df, col_a, col_b):
    if col_a in df.columns and col_b in df.columns:
        return df[col_a] / (df[col_b] + 1e-9)
    return np.nan




def safe_difference(df, col_a, col_b):
    if col_a in df.columns and col_b in df.columns:
        return df[col_a] - df[col_b]
    return np.nan




def apply_feature_engineering(df):
    d = df.copy()


    d["eng_clarif_prot_ag_ratio"] = safe_ratio(
        d,
        "clarif_014 Protein Lowry virus cult [µg/ml]",
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
    )
    d["eng_clarif_biomass_load"] = safe_product(
        d,
        "clarif_D5 8h-Cells count",
        "clarif_D3 8h-clarif. 1 Volume before [Liter]",
    )
    d["eng_clarif_ag_load"] = safe_product(
        d,
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
        "clarif_D3 8h-clarif. 1 Volume before [Liter]",
    )
    d["eng_clarif_flow_x_duration"] = safe_product(
        d,
        "clarif_Clarif 1 - Flow 340L (L/min)",
        "clarif_Clarif 1 - Duration [Minute]",
    )
    d["eng_pg_uv_cv"] = safe_ratio(
        d,
        "pg_sensor_RunCalc_UV_ForIntegral_v2_std",
        "pg_sensor_RunCalc_UV_ForIntegral_v2_mean",
    )
    d["eng2_pg_uv_range"] = safe_difference(
        d,
        "pg_sensor_RunCalc_UV_ForIntegral_v2_max",
        "pg_sensor_RunCalc_UV_ForIntegral_v2_mean",
    )
    d["eng_psv_ag_concentration"] = safe_ratio(
        d,
        "PSV_PSV - Ag total",
        "PSV_PSV - Volume ml [ml]",
    )
    d["eng2_psv_deae_purity_cascade"] = safe_product(
        d,
        "DEAE_PG - Ratio prot/Ag",
        "DEAE_PG - Purification factor",
    )


    d["eng4_clarif_ag_x_duration"] = safe_product(
        d,
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
        "clarif_Duration cells pool transfer [Minute]",
    )
    d["eng4_clarif_cells_x_duration"] = safe_product(
        d,
        "clarif_D5 8h-Cells count",
        "clarif_Duration cells pool transfer [Minute]",
    )
    d["eng4_clarif_d0_x_d5"] = safe_product(
        d,
        "clarif_D0-Cells count",
        "clarif_D5 8h-Cells count",
    )
    d["eng4_clarif_protein_x_duration"] = safe_product(
        d,
        "clarif_014 Protein Lowry virus cult [µg/ml]",
        "clarif_Duration cells pool transfer [Minute]",
    )
    d["eng4_clarif_ag_x_flow340"] = safe_product(
        d,
        "clarif_001 Ag cont Elisa virus cult [DU/ml]",
        "clarif_Clarif 1 - Flow 340L (L/min)",
    )
    d["eng4_uf_ag_elisa_x_total"] = safe_product(
        d,
        "UF_003 UF - Ag content Elisa [DU/ml]",
        "UF_UF - Ag total",
    )
    d["eng4_uf_ag_x_volume"] = safe_product(
        d,
        "UF_UF - Ag total",
        "UF_UF - Volume UFR ml [ml]",
    )
    d["eng4_uf_elisa_x_volume"] = safe_product(
        d,
        "UF_003 UF - Ag content Elisa [DU/ml]",
        "UF_UF - Volume UFR ml [ml]",
    )
    d["eng4_pg_ag_x_packing_s1"] = safe_product(
        d,
        "PG_004 PG - Ag content Elisa [DU/ml]",
        "PG_Packing quality HETP/S1 [Centimeter]",
    )
    d["eng4_pg_ag_x_packing_s2"] = safe_product(
        d,
        "PG_004 PG - Ag content Elisa [DU/ml]",
        "PG_Packing quality HETP/S2 [Centimeter]",
    )
    d["eng4_pg_temp_x_xv"] = safe_product(
        d,
        "pg_sensor_TI_A2_max",
        "pg_sensor_XV-O1_ZSO_mean",
    )
    d["eng4_pg_ag_x_accumulated_vol"] = safe_product(
        d,
        "PG_PG - Ag total",
        "pg_sensor_Accumulated Volume_max",
    )
    d["eng4_pg_fic_x_pic"] = safe_product(
        d,
        "pg_sensor_FIC_C11_mean",
        "pg_sensor_PIC_A1_mean",
    )
    d["eng4_pg_ti_a1_x_ti_a2"] = safe_product(
        d,
        "pg_sensor_TI_A1_mean",
        "pg_sensor_TI_A2_mean",
    )
    d["eng4_pg_uv_x_pi"] = safe_product(
        d,
        "pg_sensor_UV Light_std",
        "pg_sensor_PI_A2_mean",
    )
    d["eng4_pg_ai_a2_x_accumulated"] = safe_product(
        d,
        "pg_sensor_AI_A2_mean",
        "pg_sensor_Accumulated Volume_max",
    )
    d["eng4_pg_xv_x_uv_harvest"] = safe_product(
        d,
        "pg_sensor_XV-O1_ZSO_std",
        "pg_sensor_RunCalc_UV_DuringHarvest_max",
    )
    d["eng4_psv_ag_x_elisa"] = safe_product(
        d,
        "PSV_PSV - Ag total",
        "PSV_005 PSV - Ag content Elisa [DU/ml]",
    )
    d["eng4_psv_ag_x_volume"] = safe_product(
        d,
        "PSV_PSV - Ag total",
        "PSV_PSV - Volume ml [ml]",
    )
    d["eng4_psv_elisa_x_prot"] = safe_product(
        d,
        "PSV_005 PSV - Ag content Elisa [DU/ml]",
        "PSV_PSV - Prot total [mg]",
    )
    d["eng4_psv_ag_x_prot"] = safe_ratio(
        d,
        "PSV_PSV - Ag total",
        "PSV_PSV - Prot total [mg]",
    )


    return d




# ============================================================
# Data/model loading
# ============================================================
@st.cache_data
def load_dataset(ip_name):
    data_path = DATA_PATHS[ip_name]


    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")


    df = pd.read_parquet(data_path)
    df = apply_feature_engineering(df)
    df = df.reset_index(drop=True)


    return df




@st.cache_resource
def load_model_bundle(path_string):
    return joblib.load(path_string)




def get_model_bundle(ip_name, stage_name, model_display_name):
    key = (ip_name, stage_name, model_display_name)
    candidate_paths = MODEL_PATHS.get(key, [])
    model_path = find_existing_path(candidate_paths)


    if model_path is None:
        checked_paths = "\n".join(str(p) for p in candidate_paths)
        raise FileNotFoundError(
            f"No model file found for {ip_name} / {stage_name} / {model_display_name}.\n"
            f"Checked:\n{checked_paths}"
        )


    bundle = load_model_bundle(str(model_path))


    if "model" not in bundle or "features" not in bundle or "target" not in bundle:
        raise ValueError(f"Invalid model bundle format: {model_path}")


    return bundle, model_path




def detect_batch_column(df):
    candidates = [
        "BatchID",
        "Batch ID",
        "batch_id",
        "BatchId",
        "Batch",
        "batch",
        "Nr batch",
        "Nr Batch",
    ]


    normalized_columns = {
        normalize_feature_name(col): col
        for col in df.columns
    }


    for candidate in candidates:
        normalized_candidate = normalize_feature_name(candidate)
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]


    return None




def make_batch_options(df):
    batch_col = detect_batch_column(df)
    options = {}
    seen = set()


    for idx in df.index:
        if batch_col is not None:
            base_label = str(df.loc[idx, batch_col])
        else:
            base_label = f"Batch {idx + 1:03d}"


        label = base_label
        if label in seen:
            label = f"{base_label} | row {idx + 1}"


        seen.add(label)
        options[label] = idx


    return options




def resolve_shap_features(ip_name, stage_name, model_display_name, model_features, df_columns, max_features=10):
    shap_candidates = SHAP_FEATURES.get((ip_name, stage_name, model_display_name), [])


    model_features = list(model_features)
    df_columns = list(df_columns)


    model_lookup = {normalize_feature_name(f): f for f in model_features}
    df_lookup = {normalize_feature_name(f): f for f in df_columns}


    resolved = []


    for candidate in shap_candidates:
        normalized_candidate = normalize_feature_name(candidate)


        match = None


        if normalized_candidate in model_lookup:
            match = model_lookup[normalized_candidate]
        elif normalized_candidate in df_lookup and df_lookup[normalized_candidate] in model_features:
            match = df_lookup[normalized_candidate]
        else:
            for feature in model_features:
                n_feature = normalize_feature_name(feature)
                if normalized_candidate and (normalized_candidate in n_feature or n_feature in normalized_candidate):
                    match = feature
                    break


        if match is not None and match not in resolved:
            resolved.append(match)


    # Fill remaining rows from the model's own feature list so the table remains usable.
    for feature in model_features:
        if feature not in resolved and feature in df_columns:
            resolved.append(feature)
        if len(resolved) >= max_features:
            break


    return resolved[:max_features]




def create_feature_table(df, selected_row_idx, top_features, table_key):
    selected_row = df.loc[selected_row_idx]


    current_values = []
    for feature in top_features:
        value = pd.to_numeric(selected_row.get(feature, np.nan), errors="coerce")
        current_values.append(value)


    base_table = pd.DataFrame({
        "Feature": top_features,
        "Current Value": current_values,
        "New Value": [None] * len(top_features),
    })


    edited_table = st.data_editor(
        base_table,
        key=table_key,
        hide_index=True,
        use_container_width=True,
        disabled=["Feature", "Current Value"],
        column_config={
            "Feature": st.column_config.TextColumn(
                "Feature",
                width="large",
            ),
            "Current Value": st.column_config.NumberColumn(
                "Current Value",
                help="Value of the selected feature in the selected batch.",
                width="medium",
                format="%.4f",
            ),
            "New Value": st.column_config.NumberColumn(
                "New Value",
                help="Enter a new value to test. Empty cells keep the current value.",
                width="medium",
                format="%.4f",
            ),
        },
    )


    return edited_table




def build_prediction_input(df, selected_row_idx, model_features, edited_table):
    missing_features = [feature for feature in model_features if feature not in df.columns]
    if missing_features:
        raise ValueError(
            "The dataset is missing feature columns required by the model:\n"
            + "\n".join(missing_features[:25])
        )


    selected_row = df.loc[selected_row_idx].copy()
    input_values = selected_row[model_features].copy()
    input_values = pd.to_numeric(input_values, errors="coerce")


    for _, row in edited_table.iterrows():
        feature = row["Feature"]
        new_value = row["New Value"]


        if pd.notna(new_value) and feature in input_values.index:
            input_values.loc[feature] = float(new_value)


    input_df = pd.DataFrame([input_values.values], columns=model_features)
    input_df = input_df.replace([np.inf, -np.inf], np.nan)


    if input_df.isna().any().any():
        medians = df[model_features].apply(pd.to_numeric, errors="coerce").median(numeric_only=True)
        input_df = input_df.fillna(medians)


    return input_df




def predict_yield(bundle, prediction_input):
    model = bundle["model"]
    prediction = model.predict(prediction_input.values)[0]
    return float(prediction)




def get_original_yield(df, selected_row_idx, target_column):
    if target_column not in df.columns:
        return None


    value = pd.to_numeric(df.loc[selected_row_idx, target_column], errors="coerce")


    if pd.isna(value):
        return None


    return float(value)




# ============================================================
# Model results helpers
# ============================================================
def create_model_results_table(ip_name):
    columns = pd.MultiIndex.from_product(
        [MODEL_OPTIONS, ["NRMSE", "RMSE", "R²"]],
        names=["Model", "Metric"],
    )


    table = pd.DataFrame("", index=STAGES, columns=columns)
    table.index.name = "Stage"


    for stage in STAGES:
        stage_results = PERFORMANCE_RESULTS[ip_name][stage]
        best_model = min(stage_results, key=lambda model_name: stage_results[model_name]["NRMSE"])


        for model_name in MODEL_OPTIONS:
            metrics = stage_results[model_name]
            prefix = "Best⭐ " if model_name == best_model else ""


            table.loc[stage, (model_name, "NRMSE")] = f"{prefix}{metrics['NRMSE']:.4f}"
            table.loc[stage, (model_name, "RMSE")] = f"{prefix}{metrics['RMSE']:.4f}"
            table.loc[stage, (model_name, "R²")] = f"{prefix}{metrics['R²']:.4f}"


    return table




# ============================================================
# Home page
# ============================================================
def show_home_page():
    show_logo_area()


    st.markdown(
        """
        <div class="intro-label">IÉSEG x GSK Hackathon</div>
        """,
        unsafe_allow_html=True,
    )


    st.title("AI Yield Intelligence for Polio Vaccine Purification")


    st.markdown(
        """
        This application supports batch-level yield prediction for the polio vaccine purification process.
        Users can select an IP, choose a purification stage, select a batch, edit important process
        feature values, and estimate expected yield performance.
        """
    )


    st.markdown(
        """
        <div class="highlight-box">
            <h3 style="margin-top:0;">Problem Statement</h3>
            <p style="margin-bottom:0;">
                How can production process data be used to predict yield performance and help identify
                which process conditions are most associated with yield loss?
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


    col_1, col_2, col_3 = st.columns(3)


    with col_1:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-label">Global Yield Average</div>
                <div class="metric-value">34%</div>
                <div class="metric-note">Only around one-third of harvested antigen reaches final product.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


    with col_2:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-label">Yield Differs Between Batches</div>
                <div class="metric-value">±3%</div>
                <div class="metric-note">Final yield often varies by several percentage points between batches.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


    with col_3:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-label">Extra Doses From Small Improvement</div>
                <div class="metric-value">~16K doses</div>
                <div class="metric-note">Estimated additional doses from each 1 percentage-point yield improvement.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


    horizontal_line()


    st.markdown("## What the App Does")


    st.markdown(
        """
        <div class="section-box">
            <p>
                The IP1 and IP3 prediction pages work as what-if simulators. The user selects a batch,
                reviews its current feature values, enters new test values, and runs the stage-specific
                model. The result panel then compares the original yield of the selected batch with
                the predicted yield for the edited scenario.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


    horizontal_line()


    st.markdown("## Yield Variability and Key Process Signals")


    show_optional_image(
        "yield_variability.png",
        "Yield Variability Across Purification Stages",
    )


    show_optional_image(
        "top_feature_importance.png",
        "Top Process Features Supporting Yield Prediction",
    )


    st.markdown("## How to Use the App")


    st.markdown(
        """
        <div class="section-box">
            <p>
                Select IP1 Yield Prediction or IP3 Yield Prediction from the sidebar. Choose a purification
                stage, select a batch, and edit the New Value column. For Global Yield, choose the model
                to test. Click Predict to estimate the yield for the selected scenario.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )




# ============================================================
# Prediction page
# ============================================================
def show_ip_prediction_page(ip_name, selected_stage):
    st.markdown(
        f"""
        <div class="intro-label">{ip_name} Yield Prediction</div>
        """,
        unsafe_allow_html=True,
    )


    st.title(f"{ip_name} — {selected_stage} Prediction")


    st.markdown(
        """
        Select a batch, review the current feature values, and enter new values to simulate alternative
        process conditions. Empty New Value cells keep the original batch value during prediction.
        """
    )


    try:
        df = load_dataset(ip_name)
    except Exception as error:
        st.error(str(error))
        return


    control_col_1, control_col_2 = st.columns(2)


    with control_col_1:
        batch_options = make_batch_options(df)
        selected_batch_label = st.selectbox(
            "Choose batch",
            list(batch_options.keys()),
            key=f"{ip_name}_{selected_stage}_batch_select",
            help="Type to search or scroll through the available batches.",
        )
        selected_row_idx = batch_options[selected_batch_label]


    with control_col_2:
        if selected_stage == "Global Yield":
            selected_model = st.selectbox(
                "Choose model",
                MODEL_OPTIONS,
                index=MODEL_OPTIONS.index(BEST_MODEL_BY_IP_STAGE[(ip_name, selected_stage)]),
                key=f"{ip_name}_{selected_stage}_model_select",
                help="Type to search or scroll through the available model options.",
            )
        else:
            selected_model = BEST_MODEL_BY_IP_STAGE[(ip_name, selected_stage)]
            st.markdown(
                f"""
                <div class="fixed-model-box">
                    <div class="intro-label" style="margin-bottom:0.2rem;">Selected Model</div>
                    <p style="margin-bottom:0;">
                        <b>{selected_model}</b> is used for this stage based on the final modelling setup.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


    if selected_stage == "Global Yield":
        st.markdown(
            f"""
            <div class="subtle-note">
                Current selection: {ip_name} / {selected_stage} / {selected_batch_label} / {selected_model}.
                For Global Yield, the displayed top features change when the selected model changes.
            </div>
            """,
            unsafe_allow_html=True,
        )


    try:
        bundle, model_path = get_model_bundle(ip_name, selected_stage, selected_model)
    except Exception as error:
        st.error(str(error))
        return


    model_features = list(bundle["features"])
    target_column = bundle["target"]


    top_features = resolve_shap_features(
        ip_name=ip_name,
        stage_name=selected_stage,
        model_display_name=selected_model,
        model_features=model_features,
        df_columns=df.columns,
        max_features=10,
    )


    table_col, result_col = st.columns([2.35, 1])


    with table_col:
        st.markdown("### Feature Input Table")


        edited_table = create_feature_table(
            df=df,
            selected_row_idx=selected_row_idx,
            top_features=top_features,
            table_key=f"{ip_name}_{selected_stage}_{selected_batch_label}_{selected_model}_table",
        )


        predict_clicked = st.button(
            "Predict",
            type="primary",
            use_container_width=True,
            key=f"{ip_name}_{selected_stage}_{selected_batch_label}_{selected_model}_predict",
        )


    with result_col:
        original_yield = get_original_yield(df, selected_row_idx, target_column)
        predicted_yield = None


        if predict_clicked:
            try:
                prediction_input = build_prediction_input(
                    df=df,
                    selected_row_idx=selected_row_idx,
                    model_features=model_features,
                    edited_table=edited_table,
                )
                predicted_yield = predict_yield(bundle, prediction_input)
            except Exception as error:
                st.error(str(error))


        st.markdown("### Prediction Result")


        with st.container(border=True):
            if original_yield is None:
                st.metric("Original Yield", "Not available")
            else:
                st.metric("Original Yield", f"{original_yield:.2f}%")


            if predicted_yield is None:
                st.metric("Predicted Yield", "Not run yet")
                st.write("Click Predict to estimate the yield for the selected batch and feature values.")
            else:
                st.metric("Predicted Yield", f"{predicted_yield:.2f}%")


                if original_yield is not None:
                    delta = predicted_yield - original_yield
                    st.write(f"Difference from original yield: **{delta:+.2f} percentage points**.")


                st.write("Prediction generated from the selected model and edited feature values.")


            st.divider()


            st.write(f"**IP:** {ip_name}")
            st.write(f"**Stage:** {selected_stage}")
            st.write(f"**Batch:** {selected_batch_label}")
            st.write(f"**Model:** {selected_model}")




# ============================================================
# Model results page
# ============================================================
def show_model_results_page():
    st.markdown(
        """
        <div class="intro-label">Final Modeling Results</div>
        """,
        unsafe_allow_html=True,
    )


    st.title("Model Performance Summary")


    st.markdown(
        """
        This page summarizes model validation performance. NRMSE normalizes the prediction error,
        RMSE shows the average error in yield percentage points, and R² measures explained yield
        variation. Within each stage, the best model is marked based on the lowest NRMSE.
        """
    )


    ip1_tab, ip3_tab = st.tabs(["IP1", "IP3"])


    with ip1_tab:
        st.markdown("### IP1 Model Results")
        st.dataframe(
            create_model_results_table("IP1"),
            use_container_width=True,
        )


    with ip3_tab:
        st.markdown("### IP3 Model Results")
        st.dataframe(
            create_model_results_table("IP3"),
            use_container_width=True,
        )




# ============================================================
# Sidebar navigation
# ============================================================
st.sidebar.markdown("## AI Yield Intelligence")
st.sidebar.caption("IÉSEG x GSK Hackathon")


page = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "IP1 Yield Prediction",
        "IP3 Yield Prediction",
        "Model Results",
    ],
)


selected_stage = None


if page == "IP1 Yield Prediction":
    st.sidebar.markdown("### IP1 Purification Stage")
    selected_stage = st.sidebar.radio(
        "Choose a stage",
        STAGES,
        key="ip1_stage_radio",
    )


elif page == "IP3 Yield Prediction":
    st.sidebar.markdown("### IP3 Purification Stage")
    selected_stage = st.sidebar.radio(
        "Choose a stage",
        STAGES,
        key="ip3_stage_radio",
    )


st.sidebar.divider()
st.sidebar.markdown("### App Objective")
st.sidebar.write(
    "Predict yield performance from user-selected process feature values."
)




# ============================================================
# Page router
# ============================================================
if page == "Home":
    show_home_page()


elif page == "IP1 Yield Prediction":
    show_ip_prediction_page(
        ip_name="IP1",
        selected_stage=selected_stage,
    )


elif page == "IP3 Yield Prediction":
    show_ip_prediction_page(
        ip_name="IP3",
        selected_stage=selected_stage,
    )


elif page == "Model Results":
    show_model_results_page()
