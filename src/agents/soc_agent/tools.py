from datetime import UTC, datetime
from typing import Literal

import httpx
import vt
from langchain.tools import tool

from core.config import settings

MALICIOUS_THREAT_THRESHOLD = 5
SUSPICIOUS_THREAT_THRESHOLD = 3
MALICIOUS_CONFIDENCE_THRESHOLD = 50
SUSPICIOUS_CONFIDENCE_THRESHOLD = 25

_ip_blacklist = set()


@tool
def add_ip_to_blacklist(ip: str) -> str:
    """Add an IP address to the blacklist.

    Args:
        ip: The IP address to add
    """
    _ip_blacklist.add(ip)
    return f'IP {ip} added to blacklist.'


@tool
def get_all_blacklisted_ips() -> str:
    """Get all blacklisted IP addresses."""
    if not _ip_blacklist:
        return 'No IPs in the blacklist.'
    return 'Blacklisted IPs:\n' + '\n'.join(_ip_blacklist)


@tool
def is_ip_blacklisted(ip: str) -> str:
    """Check if an IP address is blacklisted.

    Args:
        ip: The IP address to check
    """
    return f'IP {ip} is {"blacklisted" if ip in _ip_blacklist else "not blacklisted"}.'


@tool
def remove_ip_from_blacklist(ip: str) -> str:
    """Remove an IP address from the blacklist.

    Args:
        ip: The IP address to remove
    """
    if ip in _ip_blacklist:
        _ip_blacklist.remove(ip)
        return f'IP {ip} removed from blacklist.'
    return f'IP {ip} not found in blacklist.'


@tool
async def virustotal_analyzer(
    indicator: str, indicator_type: Literal['url', 'ip', 'hash']
) -> str:
    """Analyze URLs, IPs, and hashes using the VirusTotal API.

    Args:
        indicator: The indicator to analyze (URL, IP, or hash)
        indicator_type: The type of indicator
    """
    try:
        async with vt.Client(settings.virustotal_api_key.get_secret_value()) as client:
            if indicator_type == 'url':
                url_id = vt.url_id(indicator)
                analysis = await client.get_object_async(f'/urls/{url_id}')
            elif indicator_type == 'ip':
                analysis = await client.get_object_async(f'/ip-addresses/{indicator}')
            elif indicator_type == 'hash':
                analysis = await client.get_object_async(f'/files/{indicator}')
            else:
                return 'Unsupported indicator type. Please use "url", "ip", or "hash".'

            malicious = analysis.last_analysis_stats.get('malicious', 0)
            suspicious = analysis.last_analysis_stats.get('suspicious', 0)
            total = sum(analysis.last_analysis_stats.values())

            if malicious > MALICIOUS_THREAT_THRESHOLD:
                threat_level = 'MALICIOUS'
            elif malicious or suspicious > SUSPICIOUS_THREAT_THRESHOLD:
                threat_level = 'SUSPICIOUS'
            else:
                threat_level = 'CLEAN'

            analysis_date = datetime.fromtimestamp(
                analysis.last_analysis_date, tz=UTC
            ).isoformat()

            return f"""VirusTotal Analysis:
Indicator: {indicator}
Detections: {malicious}/{total} malicious, {suspicious}/{total} suspicious
Classification: {threat_level}
Analysis performed on: {analysis_date}"""

    except Exception as e:
        return f'Error analyzing the indicator: {e}'


@tool
async def abuseipdb_checker(ip: str) -> str:
    """Check IP reputation using the AbuseIPDB API.

    Args:
        ip: The IP address to check
    """
    try:
        headers = {
            'Key': settings.abuseipdb_api_key.get_secret_value(),
            'Accept': 'application/json',
        }
        params = {'ipAddress': ip, 'maxAgeInDays': 90}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://api.abuseipdb.com/api/v2/check',
                headers=headers,
                params=params,
                timeout=10,
            )

            if response.is_success:
                data = response.json()['data']
                is_whitelisted = data.get('isWhitelisted', False)
                abuse_confidence = data.get('abuseConfidenceScore', 0)
                country = data.get('countryCode', 'Unknown')
                total_reports = data.get('totalReports', 0)

                level = (
                    'MALICIOUS'
                    if abuse_confidence > MALICIOUS_CONFIDENCE_THRESHOLD
                    else 'SUSPICIOUS'
                    if abuse_confidence > SUSPICIOUS_CONFIDENCE_THRESHOLD
                    else 'CLEAN'
                )
                return (
                    f'{level} - Abuse confidence: {abuse_confidence}%'
                    f' - Is whitelisted: {is_whitelisted}'
                    f' - Country code: {country}'
                    f' - Total reports: {total_reports}'
                )

            return f'Error [{response.status_code}]: {response.text}'

    except Exception as e:
        return f'Error checking IP in AbuseIPDB: {e}'
