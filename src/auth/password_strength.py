"""Password strength validation and visual feedback utilities.

Provides comprehensive password strength checking with visual indicators
for Streamlit UI integration.
"""

import re
from dataclasses import dataclass
from enum import Enum


class PasswordStrength(Enum):
    """Password strength levels."""

    VERY_WEAK = 0
    WEAK = 1
    MEDIUM = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class PasswordScore:
    """Password strength score with detailed feedback."""

    strength: PasswordStrength
    score: int  # 0-100
    feedback: list[str]
    meets_requirements: bool
    color: str
    label: str


def calculate_password_strength(password: str) -> PasswordScore:
    """Calculate comprehensive password strength score.

    Args:
        password: Plain text password

    Returns:
        PasswordScore with strength level, score, and feedback
    """
    if not password:
        return PasswordScore(
            strength=PasswordStrength.VERY_WEAK,
            score=0,
            feedback=["Password cannot be empty"],
            meets_requirements=False,
            color="#ff4444",
            label="Very Weak",
        )

    score = 0
    feedback = []
    criteria_met = {
        "length": False,
        "uppercase": False,
        "lowercase": False,
        "digit": False,
        "special": False,
    }

    # Length check (base requirement)
    length = len(password)
    if length >= 8:
        criteria_met["length"] = True
        score += 20
        if length >= 12:
            score += 10
            feedback.append("✓ Good length (12+ chars)")
        else:
            feedback.append("✓ Minimum length (8+ chars)")
    else:
        feedback.append(f"✗ Too short (need {8 - length} more chars)")

    # Character type checks
    if re.search(r"[A-Z]", password):
        criteria_met["uppercase"] = True
        score += 15
        feedback.append("✓ Contains uppercase letters")
    else:
        feedback.append("✗ Add uppercase letters (A-Z)")

    if re.search(r"[a-z]", password):
        criteria_met["lowercase"] = True
        score += 15
        feedback.append("✓ Contains lowercase letters")
    else:
        feedback.append("✗ Add lowercase letters (a-z)")

    if re.search(r"\d", password):
        criteria_met["digit"] = True
        score += 15
        feedback.append("✓ Contains numbers")
    else:
        feedback.append("✗ Add numbers (0-9)")

    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        criteria_met["special"] = True
        score += 15
        feedback.append("✓ Contains special characters")
    else:
        feedback.append("✗ Add special characters (!@#$ etc)")

    # Bonus points for complexity
    # Check for multiple character types mixed together
    if length >= 12 and sum(criteria_met.values()) >= 4:
        score += 10
        feedback.append("✓ Strong character mix")

    # Penalty for common patterns
    common_patterns = [
        r"(.)\1{2,}",  # Repeated characters (aaa, 111)
        r"(abc|bcd|cde|def|123|234|345|456|567|678|789)",  # Sequential patterns
        r"(password|admin|user|test|demo)",  # Common words (case-insensitive)
    ]

    for pattern in common_patterns:
        if re.search(pattern, password, re.IGNORECASE):
            score = max(0, score - 10)
            feedback.append("⚠ Avoid common patterns")
            break

    # Determine strength level
    if score >= 85:
        strength = PasswordStrength.VERY_STRONG
        color = "#00cc66"
        label = "Very Strong"
    elif score >= 70:
        strength = PasswordStrength.STRONG
        color = "#66cc00"
        label = "Strong"
    elif score >= 50:
        strength = PasswordStrength.MEDIUM
        color = "#ffaa00"
        label = "Medium"
    elif score >= 30:
        strength = PasswordStrength.WEAK
        color = "#ff6600"
        label = "Weak"
    else:
        strength = PasswordStrength.VERY_WEAK
        color = "#ff4444"
        label = "Very Weak"

    # Check if meets minimum requirements (for registration/reset)
    meets_requirements = (
        criteria_met["length"]
        and criteria_met["uppercase"]
        and criteria_met["lowercase"]
        and criteria_met["digit"]
        and criteria_met["special"]
    )

    return PasswordScore(
        strength=strength,
        score=min(100, score),
        feedback=feedback,
        meets_requirements=meets_requirements,
        color=color,
        label=label,
    )


def render_password_strength_meter(password: str) -> str:
    """Render password strength meter as HTML/CSS.

    Args:
        password: Plain text password

    Returns:
        HTML string with styled password strength meter
    """
    score_data = calculate_password_strength(password)

    # Generate feedback list HTML
    feedback_html = "\n".join(
        [
            f'<li style="font-size: 13px; color: {"#00aa00" if "✓" in item else "#cc0000"};">{item}</li>'
            for item in score_data.feedback
        ]
    )

    # Build requirements status HTML
    if password:
        bg_color = "#d4edda" if score_data.meets_requirements else "#fff3cd"
        border_color = "#c3e6cb" if score_data.meets_requirements else "#ffeaa7"
        text_color = "#155724" if score_data.meets_requirements else "#856404"
        status_text = (
            "✓ Password meets all requirements"
            if score_data.meets_requirements
            else "⚠ Password must meet all requirements above"
        )
        requirements_html = f"""
        <div style="margin-top: 12px; padding: 10px; background: {bg_color}; border-radius: 6px; border: 1px solid {border_color};">
            <span style="font-size: 13px; color: {text_color}; font-weight: 500;">
                {status_text}
            </span>
        </div>"""
    else:
        requirements_html = ""

    html = f"""
    <div style="margin: 10px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e0e0e0;">
        <div style="margin-bottom: 8px;">
            <span style="font-weight: 600; font-size: 14px;">Password Strength:</span>
            <span style="color: {score_data.color}; font-weight: bold; font-size: 14px; margin-left: 8px;">
                {score_data.label} ({score_data.score}/100)
            </span>
        </div>

        <!-- Progress bar -->
        <div style="width: 100%; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; margin-bottom: 12px;">
            <div style="width: {score_data.score}%; height: 100%; background: {score_data.color}; transition: width 0.3s ease;"></div>
        </div>

        <!-- Feedback list -->
        <ul style="margin: 0; padding-left: 20px; list-style: none;">
            {feedback_html}
        </ul>

        {requirements_html}
    </div>
    """

    return html


def is_password_strong(password: str) -> tuple[bool, str]:
    """Check if password meets minimum security requirements.

    This is the main validation function used for registration and password reset.

    Args:
        password: Plain text password

    Returns:
        Tuple of (is_strong, message)
    """
    score_data = calculate_password_strength(password)

    if not score_data.meets_requirements:
        # Return first error message
        error_messages = [msg.replace("✗ ", "") for msg in score_data.feedback if "✗" in msg]
        if error_messages:
            return (False, error_messages[0])
        return (False, "Password does not meet minimum requirements.")

    # Additional check for very weak passwords even if they meet basic criteria
    if score_data.strength == PasswordStrength.VERY_WEAK:
        return (
            False,
            "Password is too weak. Please avoid common patterns and use a stronger combination.",
        )

    return (True, f"Password is {score_data.label.lower()}.")
