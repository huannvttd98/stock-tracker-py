"""
Vietnam stock market sector classification.
Maps sector names to lists of ticker symbols (major stocks per sector).
"""

from typing import Optional


SECTORS = {
    "Ngan hang": [
        "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB", "HDB",
        "TPB", "LPB", "SHB", "EIB", "MSB", "OCB", "VIB", "BAB", "ABB",
        "NAB", "PGB", "SSB", "BVB", "KLB",
    ],
    "Bat dong san": [
        "VIC", "VHM", "NVL", "KDH", "DXG", "NLG", "HDG", "DIG", "IJC",
        "CEO", "PDR", "SCR", "NBB", "LDG", "QCG", "TDC", "HDC", "KBC",
        "BCG", "DXS", "AGG", "VRE", "SSH",
    ],
    "Chung khoan": [
        "SSI", "VND", "HCM", "VCI", "SHS", "MBS", "CTS", "BSI", "FTS",
        "ORS", "AGR", "APG", "TVS", "VIX", "DSC", "TCI",
    ],
    "Thep & Vat lieu XD": [
        "HPG", "HSG", "NKG", "TLH", "SMC", "DTL", "POM", "VGS",
        "HMC", "TVN",
    ],
    "Cong nghe": [
        "FPT", "CMG", "ELC", "ITD", "VGI", "FOX",
    ],
    "Dien & Nang luong": [
        "POW", "GEG", "REE", "PC1", "PPC", "NT2", "HND", "VSH",
        "SJD", "TTA", "BCG", "HDG",
    ],
    "Dau khi": [
        "GAS", "PLX", "PVD", "PVS", "PVT", "BSR", "OIL", "PVC",
        "PVB", "PVG",
    ],
    "Thuc pham & Do uong": [
        "VNM", "MSN", "SAB", "KDC", "QNS", "MCH", "VHC",
        "ANV", "IDI", "ASM", "HAG", "HNG",
    ],
    "Xay dung & Ha tang": [
        "CTD", "HBC", "VCG", "FCN", "LCG", "CII", "C4G", "HHV",
        "VC3", "VCS",
    ],
    "Van tai & Logistics": [
        "VTP", "GMD", "HAH", "VOS", "VNA", "SGN", "ACV", "SCS",
        "MVN",
    ],
    "Cao su & Nong nghiep": [
        "GVR", "DPR", "PHR", "TRC", "BRC", "HRC",
        "HAG", "HNG", "SBT", "LSS",
    ],
    "Bao hiem": [
        "BVH", "BMI", "PVI", "MIG", "BIC", "PTI", "ABI",
    ],
    "Duoc pham & Y te": [
        "DHG", "DMC", "IMP", "TRA", "DBD", "PME", "DVN",
        "PHC", "DCL",
    ],
    "Det may & Giay da": [
        "TCM", "STK", "VGT", "TNG", "MSH", "GIL", "TVT",
    ],
}


def get_sector_for_symbol(symbol: str) -> Optional[str]:
    """Return the sector name for a given symbol, or None."""
    symbol = symbol.upper()
    for sector, symbols in SECTORS.items():
        if symbol in symbols:
            return sector
    return None
