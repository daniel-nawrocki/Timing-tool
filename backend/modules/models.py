from dataclasses import dataclass

@dataclass
class Hole:
    id: int
    depth: float
    diameter: float
    explosive_type: str
    position: tuple[float, float]  # (x, y)

@dataclass
class Row:
    id: int
    holes: list[Hole]

@dataclass
class HoleTiming:
    hole_id: int
    timing_data: dict  # key: time_type, value: time_value

@dataclass
class ConflictInfo:
    hole_id: int
    description: str
    resolution_steps: list[str]

@dataclass
class OptimizationMetrics:
    metric_name: str
    value: float
    units: str

@dataclass
class BlastData:
    date: str
    location: str
    rows: list[Row]
    hole_timings: list[HoleTiming]

@dataclass
class OptimizationResult:
    success: bool
    metrics: list[OptimizationMetrics]
    details: str
