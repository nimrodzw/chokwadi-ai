"""
Chokwadi AI - Link Scanner
Cybersecurity module for URL/link analysis and phishing detection
"""
import re
from urllib.parse import urlparse


# Known legitimate Zimbabwean domains for comparison
LEGITIMATE_ZW_DOMAINS = {
    "ecocash.co.zw", "innbucks.co.zw", "rbz.co.zw", "zimra.co.zw",
    "zse.co.zw", "herald.co.zw", "chronicle.co.zw", "newsday.co.zw",
    "techzim.co.zw", "zbc.co.zw", "parlzim.gov.zw", "zimgov.gov.zw",
    "mhte.gov.zw", "mohcc.gov.zw", "potraz.gov.zw", "zec.org.zw",
    "uz.ac.zw", "nust.ac.zw", "hit.ac.zw", "msu.ac.zw",
    "steward.co.zw", "cbz.co.zw", "stanbicbank.co.zw", "zetdc.co.zw",
    "econet.co.zw", "netone.co.zw", "telecel.co.zw",
}

# Common phishing TLDs and patterns
SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".club", ".work", ".click", ".link",
    ".buzz", ".gq", ".ml", ".cf", ".tk", ".ga",
}

# Known scam URL patterns in Zimbabwe
SCAM_PATTERNS = [
    r"ecocash.*free",
    r"innbucks.*bonus",
    r"zim.*lottery",
    r"dv[-_]?lottery.*apply",
    r"rbz.*zig.*exchange",
    r"free[-_]?airtime",
    r"zimra.*refund",
    r"zesa.*free.*tokens?",
    r"diaspora.*send.*money",
    r"forex.*guaranteed.*profit",
    r"crypto.*invest.*zim",
    r"whatsapp.*gold",
]


def scan_url(url: str) -> dict:
    """
    Perform security analysis on a URL.
    
    Args:
        url: The URL to analyse
    
    Returns:
        dict with security findings
    """
    findings = {
        "url": url,
        "risk_level": "low",  # low, medium, high, critical
        "issues": [],
        "details": {}
    }
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        full_url_lower = url.lower()
        
        # --- Check 1: Missing HTTPS ---
        if parsed.scheme == "http":
            findings["issues"].append("No HTTPS encryption - data sent insecurely")
            _escalate_risk(findings, "medium")
        
        # --- Check 2: Suspicious TLD ---
        for tld in SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                findings["issues"].append(f"Suspicious domain extension ({tld}) commonly used in scams")
                _escalate_risk(findings, "high")
                break
        
        # --- Check 3: Typosquatting detection ---
        typosquat = _check_typosquatting(domain)
        if typosquat:
            findings["issues"].append(
                f"Possible impersonation of '{typosquat}' - domain looks similar but isn't the real site"
            )
            _escalate_risk(findings, "critical")
        
        # --- Check 4: Known scam patterns ---
        for pattern in SCAM_PATTERNS:
            if re.search(pattern, full_url_lower):
                findings["issues"].append(
                    "URL matches known Zimbabwean scam/fraud patterns"
                )
                _escalate_risk(findings, "high")
                break
        
        # --- Check 5: URL length and complexity ---
        if len(url) > 200:
            findings["issues"].append("Unusually long URL - may be disguising destination")
            _escalate_risk(findings, "medium")
        
        # --- Check 6: Suspicious path elements ---
        sus_paths = ["login", "signin", "verify", "update", "secure", "account", "confirm"]
        for sus in sus_paths:
            if sus in path and domain not in LEGITIMATE_ZW_DOMAINS:
                findings["issues"].append(
                    f"Contains '{sus}' in path on non-official domain - possible phishing"
                )
                _escalate_risk(findings, "high")
                break
        
        # --- Check 7: IP address instead of domain ---
        if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
            findings["issues"].append("Uses IP address instead of domain name - highly suspicious")
            _escalate_risk(findings, "critical")
        
        # --- Check 8: Excessive subdomains ---
        if domain.count('.') > 3:
            findings["issues"].append("Excessive subdomains - may be impersonating a legitimate site")
            _escalate_risk(findings, "medium")
        
        # --- Check 9: URL shortener ---
        shorteners = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "rb.gy", "shorturl.at"]
        if any(s in domain for s in shorteners):
            findings["issues"].append("Uses URL shortener - destination is hidden")
            _escalate_risk(findings, "medium")
        
        # --- Summary ---
        if not findings["issues"]:
            findings["issues"].append("No obvious red flags detected - but always verify independently")
        
        findings["details"] = {
            "domain": domain,
            "scheme": parsed.scheme,
            "is_known_zw_domain": domain in LEGITIMATE_ZW_DOMAINS,
        }
    
    except Exception as e:
        findings["issues"].append(f"Could not fully analyse URL: {str(e)}")
        _escalate_risk(findings, "medium")
    
    return findings


def _escalate_risk(findings: dict, new_level: str):
    """Escalate risk level (only goes up, never down)."""
    levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if levels.get(new_level, 0) > levels.get(findings["risk_level"], 0):
        findings["risk_level"] = new_level


def _check_typosquatting(domain: str) -> str | None:
    """Check if a domain is a typosquat of a known Zimbabwean domain."""
    # Simple Levenshtein-like check for common targets
    typosquat_targets = {
        "ecocash": "ecocash.co.zw",
        "innbucks": "innbucks.co.zw",
        "econet": "econet.co.zw",
        "cbz": "cbz.co.zw",
        "steward": "steward.co.zw",
        "zimra": "zimra.co.zw",
        "rbz": "rbz.co.zw",
    }
    
    domain_base = domain.split('.')[0].lower()
    
    for target_base, target_full in typosquat_targets.items():
        if domain not in LEGITIMATE_ZW_DOMAINS:
            # Check for common typosquatting: character substitution, extra chars
            if (target_base in domain_base and domain_base != target_base) or \
               (_levenshtein_distance(domain_base, target_base) <= 2 and domain_base != target_base):
                return target_full
    
    return None


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    
    return prev_row[-1]


def format_scan_results(scan: dict) -> str:
    """Format scan results for inclusion in AI prompt."""
    risk_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴",
        "critical": "🚨"
    }
    
    result = f"AUTOMATED SECURITY SCAN RESULTS:\n"
    result += f"Risk Level: {risk_emoji.get(scan['risk_level'], '⚪')} {scan['risk_level'].upper()}\n"
    result += f"Issues found:\n"
    for issue in scan["issues"]:
        result += f"  - {issue}\n"
    
    if scan.get("details", {}).get("is_known_zw_domain"):
        result += f"  ✅ Domain is a known legitimate Zimbabwean website\n"
    
    return result
