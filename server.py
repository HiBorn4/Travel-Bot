# ----------  server.py  ----------
from mcp.server.fastmcp import FastMCP
from loguru import logger
import json
from utils import (
    check_trip_validity,
    post_es_get,
    post_es_final,
    cancel_trip,
)

mcp = FastMCP("Travel APIs")

# ----------  Pure API tools ----------
@mcp.tool()
def check_trip_validity_tool(
    pernr: str, dept_date: str, arr_date: str, dept_time: str, arr_time: str
) -> str:
    ok, remarks = check_trip_validity(pernr, dept_date, arr_date, dept_time, arr_time)
    return json.dumps({"valid": ok, "remarks": remarks})

@mcp.tool()
def post_es_get_tool(travel: dict, pernr: str) -> str:
    ok, reason = post_es_get(travel, pernr)
    return json.dumps({"ok": ok, "reason": reason})

@mcp.tool()
def post_es_final_tool(travel: dict, pernr: str) -> str:
    ok, reason = post_es_final(travel, pernr)
    return json.dumps({"ok": ok, "reason": reason})

@mcp.tool()
def cancel_trip_tool(trip_json: dict) -> str:
    ok, result = cancel_trip(trip_json)
    return json.dumps({"ok": ok, "data": result})

if __name__ == "__main__":
    mcp.run(transport="stdio")