"""Safe, whitelist-driven custom report builder.

The custom builder never interpolates user-supplied identifiers into SQL. A
fixed registry of DATASETS declares the allowed base tables, the selectable
columns (with their SQL expressions) and the filterable fields with their
allowed operators. `build_query` validates every requested column/field/
operator against that registry and binds all *values* as parameters — so the
worst a malicious payload can do is get a 422.
"""

from dataclasses import dataclass, field

# operator key -> (SQL template using {col} and a bound :param, wraps_value)
_OPERATORS: dict[str, str] = {
    "eq": "{col} = :{p}",
    "ne": "{col} <> :{p}",
    "gt": "{col} > :{p}",
    "gte": "{col} >= :{p}",
    "lt": "{col} < :{p}",
    "lte": "{col} <= :{p}",
    "contains": "{col} ilike :{p}",
}
MAX_LIMIT = 1000


@dataclass(frozen=True)
class Column:
    label: str
    expr: str  # SQL expression, aliased to the column key on output


@dataclass(frozen=True)
class Filter:
    label: str
    expr: str            # SQL expression the operator is applied to
    ops: tuple[str, ...]  # allowed operator keys


@dataclass(frozen=True)
class Dataset:
    key: str
    name: str
    base: str  # full FROM ... [static WHERE ...] clause
    columns: dict[str, Column]
    filters: dict[str, Filter] = field(default_factory=dict)
    default_order: str = ""


_NAME = "trim(concat(e.first_name,' ',coalesce(e.last_name,'')))"

DATASETS: dict[str, Dataset] = {
    "employees": Dataset(
        key="employees",
        name="Employees",
        base="from ihrms.v_employee e",
        columns={
            "employee_code": Column("Code", "e.employee_code"),
            "name": Column("Name", f"{_NAME}"),
            "designation": Column("Designation", "e.designation_c"),
            "department": Column("Department", "e.department_c"),
            "branch": Column("Branch", "e.branch_c"),
            "date_of_joining": Column("Joined", "e.date_of_joining"),
            "is_active": Column("Active", "e.is_active"),
        },
        filters={
            "department": Filter("Department", "e.department_c", ("eq", "ne", "contains")),
            "designation": Filter("Designation", "e.designation_c", ("eq", "contains")),
            "branch": Filter("Branch", "e.branch_c", ("eq", "contains")),
            "date_of_joining": Filter("Joined", "e.date_of_joining", ("gte", "lte", "eq")),
            "is_active": Filter("Active", "e.is_active", ("eq",)),
        },
        default_order="e.date_of_joining desc nulls last",
    ),
    "leave_requests": Dataset(
        key="leave_requests",
        name="Leave requests",
        base=("from ihrms.leave_request lr "
              "join ihrms.leave_type lt on lt.id = lr.leave_type_id "
              "left join public.employees e on e.employee_id = lr.employee_id"),
        columns={
            "name": Column("Employee", f"{_NAME}"),
            "leave_code": Column("Type", "lt.code"),
            "from_date": Column("From", "lr.from_date"),
            "to_date": Column("To", "lr.to_date"),
            "days": Column("Days", "lr.days"),
            "status": Column("Status", "lr.status"),
        },
        filters={
            "status": Filter("Status", "lr.status", ("eq", "ne")),
            "leave_code": Filter("Type", "lt.code", ("eq",)),
            "from_date": Filter("From", "lr.from_date", ("gte", "lte")),
        },
        default_order="lr.from_date desc",
    ),
    "payslips_latest": Dataset(
        key="payslips_latest",
        name="Payslips (latest run)",
        base=("from ihrms.payslip p "
              "join ihrms.payroll_run r on r.id = p.run_id "
              "left join public.employees e on e.employee_id = p.employee_id "
              "where r.id = (select id from ihrms.payroll_run "
              "order by period_year desc, period_month desc limit 1)"),
        columns={
            "name": Column("Employee", f"{_NAME}"),
            "gross": Column("Gross", "p.gross"),
            "total_deductions": Column("Deductions", "p.total_deductions"),
            "net_pay": Column("Net pay", "p.net_pay"),
        },
        filters={
            "net_pay": Filter("Net pay", "p.net_pay", ("gte", "lte")),
        },
        default_order="p.net_pay desc",
    ),
}


def build_query(
    dataset_key: str,
    columns: list[str],
    filters: list[dict[str, str]],
    limit: int = 200,
) -> tuple[str, dict[str, object], list[str]]:
    """Validate a build spec against the whitelist and return (sql, params, columns).

    Raises ValueError (-> 422 at the API) for any unknown dataset, column,
    filter field or operator. All values are bound parameters.
    """
    ds = DATASETS.get(dataset_key)
    if ds is None:
        raise ValueError(f"Unknown dataset '{dataset_key}'")

    chosen = columns or list(ds.columns)
    for c in chosen:
        if c not in ds.columns:
            raise ValueError(f"Unknown column '{c}' for dataset '{dataset_key}'")

    select_sql = ", ".join(f'{ds.columns[c].expr} as "{c}"' for c in chosen)

    where_parts: list[str] = []
    params: dict[str, object] = {}
    for i, f in enumerate(filters):
        fld, op, val = f.get("field"), f.get("op"), f.get("value")
        if fld not in ds.filters:
            raise ValueError(f"Unknown filter field '{fld}'")
        spec = ds.filters[fld]
        if op not in spec.ops:
            raise ValueError(f"Operator '{op}' not allowed on '{fld}'")
        pkey = f"p{i}"
        params[pkey] = f"%{val}%" if op == "contains" else val
        where_parts.append(_OPERATORS[op].format(col=spec.expr, p=pkey))

    # base may already contain a static WHERE; join extra predicates with AND
    connector = " and " if " where " in ds.base.lower() else " where "
    where_sql = (connector + " and ".join(where_parts)) if where_parts else ""
    order_sql = f" order by {ds.default_order}" if ds.default_order else ""
    safe_limit = max(1, min(int(limit), MAX_LIMIT))

    sql = f"select {select_sql} {ds.base}{where_sql}{order_sql} limit {safe_limit}"
    return sql, params, chosen
