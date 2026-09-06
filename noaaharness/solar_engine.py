"""
NOAA Solar Calculator Engine
Based on Jean Meeus's Astronomical Algorithms as implemented by NOAA Global Monitoring Laboratory
and the reference implementation in index.html.

Calculates:
- Julian Day & Julian Century
- Solar Declination & Equation of Time
- Solar Noon (เที่ยงวันจริง)
- Sunrise / Sunset (พระอาทิตย์ขึ้น / พระอาทิตย์ตก)
- Civil, Nautical, Astronomical Twilights (สนธยาพลเรือน, เดินเรือ, ดาราศาสตร์)
- Sun Azimuth at Sunrise / Sunset (ทิศอะซิมุท)
- Day Length (ความยาวกลางวัน)
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

D2R = math.pi / 180.0
R2D = 180.0 / math.pi


def sin_d(d: float) -> float:
    return math.sin(d * D2R)


def cos_d(d: float) -> float:
    return math.cos(d * D2R)


def tan_d(d: float) -> float:
    return math.tan(d * D2R)


def asin_d(x: float) -> float:
    clamped = max(-1.0, min(1.0, x))
    return math.asin(clamped) * R2D


def acos_d(x: float) -> float:
    clamped = max(-1.0, min(1.0, x))
    return math.acos(clamped) * R2D


def mod360(x: float) -> float:
    return ((x % 360.0) + 360.0) % 360.0


def julian_day(year: int, month: int, day: int) -> float:
    """
    Step 1: Calculate Julian Day at 00:00 UT
    Exact formula from index.html (Jean Meeus algorithm)
    """
    y = year
    m = month
    d = day
    if m <= 2:
        y -= 1
        m += 12
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


@dataclass
class SolarCalculationResult:
    # Inputs
    latitude: float
    longitude: float
    timezone_offset: float
    year: int
    month: int
    day: int

    # 12-step intermediate variables
    julian_day_noon: float       # JD at local noon
    julian_century: float        # T
    geom_mean_long_sun: float    # L0 (degrees)
    geom_mean_anom_sun: float    # M0 (degrees)
    eccentricity: float          # ec
    eq_of_center: float          # C (degrees)
    sun_true_long: float         # TL (degrees)
    omega: float                 # om (degrees)
    sun_app_long: float          # lam (degrees)
    mean_obliq_ecliptic: float   # e0 (degrees)
    obliq_corr: float            # eps (degrees)
    solar_declination: float     # dec (degrees)
    var_y: float                 # yv = tan^2(eps / 2)
    equation_of_time: float      # EoT (minutes)

    # Key Solar Events (minutes from midnight in local time)
    solar_noon_min: float
    hour_angle_deg: Optional[float]
    sunrise_min: Optional[float]
    sunset_min: Optional[float]

    # Twilights (minutes from midnight)
    civil_twilight_morning_min: Optional[float]
    civil_twilight_evening_min: Optional[float]
    nautical_twilight_morning_min: Optional[float]
    nautical_twilight_evening_min: Optional[float]
    astronomical_twilight_morning_min: Optional[float]
    astronomical_twilight_evening_min: Optional[float]

    # Azimuth at rise & set (0 = North, 90 = East, 180 = South, 270 = West)
    azimuth_rise_deg: Optional[float]
    azimuth_set_deg: Optional[float]

    # Day length in minutes
    day_length_min: Optional[float]

    # Condition flags
    is_polar_day: bool = False
    is_polar_night: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone_offset": self.timezone_offset,
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "julian_day_noon": self.julian_day_noon,
            "julian_century": self.julian_century,
            "geom_mean_long_sun_deg": self.geom_mean_long_sun,
            "geom_mean_anom_sun_deg": self.geom_mean_anom_sun,
            "eccentricity": self.eccentricity,
            "eq_of_center_deg": self.eq_of_center,
            "sun_true_long_deg": self.sun_true_long,
            "omega_deg": self.omega,
            "sun_app_long_deg": self.sun_app_long,
            "mean_obliq_ecliptic_deg": self.mean_obliq_ecliptic,
            "obliq_corr_deg": self.obliq_corr,
            "solar_declination_deg": self.solar_declination,
            "var_y": self.var_y,
            "equation_of_time_min": self.equation_of_time,
            "solar_noon_min": self.solar_noon_min,
            "hour_angle_deg": self.hour_angle_deg,
            "sunrise_min": self.sunrise_min,
            "sunset_min": self.sunset_min,
            "day_length_min": self.day_length_min,
            "azimuth_rise_deg": self.azimuth_rise_deg,
            "azimuth_set_deg": self.azimuth_set_deg,
            "civil_twilight_morning_min": self.civil_twilight_morning_min,
            "civil_twilight_evening_min": self.civil_twilight_evening_min,
            "nautical_twilight_morning_min": self.nautical_twilight_morning_min,
            "nautical_twilight_evening_min": self.nautical_twilight_evening_min,
            "astronomical_twilight_morning_min": self.astronomical_twilight_morning_min,
            "astronomical_twilight_evening_min": self.astronomical_twilight_evening_min,
            "is_polar_day": self.is_polar_day,
            "is_polar_night": self.is_polar_night,
            "formatted": {
                "solar_noon": minutes_to_hms(self.solar_noon_min),
                "sunrise": minutes_to_hms(self.sunrise_min),
                "sunset": minutes_to_hms(self.sunset_min),
                "solar_noon_hm": minutes_to_hm(self.solar_noon_min),
                "sunrise_hm": minutes_to_hm(self.sunrise_min),
                "sunset_hm": minutes_to_hm(self.sunset_min),
                "day_length": minutes_to_duration_th(self.day_length_min),
                "civil_twilight_morning": minutes_to_hms(self.civil_twilight_morning_min),
                "civil_twilight_evening": minutes_to_hms(self.civil_twilight_evening_min),
                "nautical_twilight_morning": minutes_to_hms(self.nautical_twilight_morning_min),
                "nautical_twilight_evening": minutes_to_hms(self.nautical_twilight_evening_min),
                "astronomical_twilight_morning": minutes_to_hms(self.astronomical_twilight_morning_min),
                "astronomical_twilight_evening": minutes_to_hms(self.astronomical_twilight_evening_min),
            }
        }


def calculate_solar(
    latitude: float,
    longitude: float,
    timezone_offset: float,
    year: int,
    month: int,
    day: int
) -> SolarCalculationResult:
    """
    Calculate solar position and events using NOAA Solar Calculator 12 steps.
    Identical logic to index.html solar() function.
    """
    # 1) Julian Day at local solar noon
    jd_0h = julian_day(year, month, day)
    jd_noon = jd_0h + (12.0 - timezone_offset) / 24.0

    # 2) Julian Century
    t = (jd_noon - 2451545.0) / 36525.0

    # 3) Geometric Mean Longitude of Sun (L0) in degrees
    l0 = mod360(280.46646 + t * (36000.76983 + t * 0.0003032))

    # 4) Geometric Mean Anomaly of Sun (M0) in degrees
    m0 = 357.52911 + t * (35999.05029 - 0.0001537 * t)

    # 5) Eccentricity of Earth's orbit
    ec = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    # 6) Equation of Center (C) in degrees
    c = (
        sin_d(m0) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + sin_d(2.0 * m0) * (0.019993 - 0.000101 * t)
        + sin_d(3.0 * m0) * 0.000289
    )

    # 7) Sun True Longitude (TL) in degrees
    tl = l0 + c

    # 8) Apparent Longitude (lam) in degrees
    om = 125.04 - 1934.136 * t
    lam = tl - 0.00569 - 0.00478 * sin_d(om)

    # 9) Obliquity of Ecliptic (eps) in degrees
    e0 = 23.0 + (26.0 + ((21.448 - t * (46.815 + t * (0.00059 - t * 0.001813)))) / 60.0) / 60.0
    eps = e0 + 0.00256 * cos_d(om)

    # 10) Solar Declination (dec) in degrees
    dec = asin_d(sin_d(eps) * sin_d(lam))

    # 11) Equation of Time (EoT) in minutes
    yv = math.pow(tan_d(eps / 2.0), 2)
    eot = 4.0 * R2D * (
        yv * sin_d(2.0 * l0)
        - 2.0 * ec * sin_d(m0)
        + 4.0 * ec * yv * sin_d(m0) * cos_d(2.0 * l0)
        - 0.5 * yv * yv * sin_d(4.0 * l0)
        - 1.25 * ec * ec * sin_d(2.0 * m0)
    )

    # Solar Noon in minutes from midnight (local time)
    solar_noon = 720.0 - 4.0 * longitude - eot + timezone_offset * 60.0

    # 12) Hour Angle for given zenith angle (z)
    def hour_angle(z: float) -> Optional[float]:
        cos_lat = cos_d(latitude)
        cos_dec = cos_d(dec)
        if abs(cos_lat * cos_dec) < 1e-12:
            return None
        cos_ha = cos_d(z) / (cos_lat * cos_dec) - tan_d(latitude) * tan_d(dec)
        if cos_ha > 1.0 or cos_ha < -1.0:
            return None
        return acos_d(cos_ha)

    def pair(z: float) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        ha = hour_angle(z)
        if ha is None:
            return None, None, None
        return solar_noon - 4.0 * ha, solar_noon + 4.0 * ha, ha

    # Standard sunrise & sunset: zenith = 90.833°
    # (Atmospheric refraction 0.567° + Sun solar disc radius 0.266°)
    rise, set_, h_val = pair(90.833)

    # Civil twilight: zenith = 96°
    cv_a, cv_b, _ = pair(96.0)

    # Nautical twilight: zenith = 102°
    nt_a, nt_b, _ = pair(102.0)

    # Astronomical twilight: zenith = 108°
    as_a, as_b, _ = pair(108.0)

    # Solar Azimuth at sunrise and sunset
    az_r: Optional[float] = None
    az_s: Optional[float] = None
    if rise is not None:
        h_alt = -0.833
        denom = cos_d(latitude) * cos_d(h_alt)
        if abs(denom) > 1e-12:
            cos_az = (sin_d(dec) - sin_d(latitude) * sin_d(h_alt)) / denom
            cos_az = max(-1.0, min(1.0, cos_az))
            az_r = acos_d(cos_az)
            az_s = 360.0 - az_r

    # Day length
    day_len = None if rise is None or set_ is None else (set_ - rise)

    # Polar day/night detection
    is_polar_day = False
    is_polar_night = False
    if rise is None:
        noon_altitude = 90.0 - latitude + dec if latitude >= 0 else 90.0 + latitude - dec
        if noon_altitude > 0:
            is_polar_day = True
        else:
            is_polar_night = True

    return SolarCalculationResult(
        latitude=latitude,
        longitude=longitude,
        timezone_offset=timezone_offset,
        year=year,
        month=month,
        day=day,
        julian_day_noon=jd_noon,
        julian_century=t,
        geom_mean_long_sun=l0,
        geom_mean_anom_sun=m0,
        eccentricity=ec,
        eq_of_center=c,
        sun_true_long=tl,
        omega=om,
        sun_app_long=lam,
        mean_obliq_ecliptic=e0,
        obliq_corr=eps,
        solar_declination=dec,
        var_y=yv,
        equation_of_time=eot,
        solar_noon_min=solar_noon,
        hour_angle_deg=h_val,
        sunrise_min=rise,
        sunset_min=set_,
        civil_twilight_morning_min=cv_a,
        civil_twilight_evening_min=cv_b,
        nautical_twilight_morning_min=nt_a,
        nautical_twilight_evening_min=nt_b,
        astronomical_twilight_morning_min=as_a,
        astronomical_twilight_evening_min=as_b,
        azimuth_rise_deg=az_r,
        azimuth_set_deg=az_s,
        day_length_min=day_len,
        is_polar_day=is_polar_day,
        is_polar_night=is_polar_night,
    )


def minutes_to_hms(minutes: Optional[float]) -> str:
    """Format minutes from midnight to HH:MM:SS with matching rounding logic from index.html"""
    if minutes is None or math.isnan(minutes):
        return "—"
    m = ((minutes % 1440.0) + 1440.0) % 1440.0
    h = int(m // 60)
    mi = int(m % 60)
    s = round(((m % 60) - mi) * 60)
    if s >= 60:
        s = 59
    return f"{h:02d}:{mi:02d}:{s:02d}"


def minutes_to_hm(minutes: Optional[float]) -> str:
    """Format minutes from midnight to HH:MM (e.g. 06:20)"""
    full = minutes_to_hms(minutes)
    if full == "—":
        return "—"
    return full[:5]


def minutes_to_duration_th(minutes: Optional[float]) -> str:
    """Format duration into Thai string: X ชั่วโมง Y นาที"""
    if minutes is None or math.isnan(minutes):
        return "—"
    m_round = round(minutes)
    h = int(m_round // 60)
    mi = int(m_round % 60)
    return f"{h} ชั่วโมง {mi} นาที"
