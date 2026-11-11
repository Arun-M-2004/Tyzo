import json

from flask import Blueprint, jsonify, request

from backend.services.database import get_connection


ticket_bp = Blueprint("ticket", __name__)


# --------------------------------------------------
# GET ALL DATASETS
# URL: GET /api/datasets
# --------------------------------------------------

@ticket_bp.route("/datasets", methods=["GET"])
def get_datasets():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                dataset_name,
                original_filename,
                total_tickets,
                uploaded_at
            FROM datasets
            ORDER BY id DESC
        """)

        datasets = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "success": True,
            "total_datasets": len(datasets),
            "datasets": datasets
        })

    finally:
        connection.close()


# --------------------------------------------------
# GET TICKETS WITH FILTERS AND PAGINATION
# URL: GET /api/tickets
# --------------------------------------------------

@ticket_bp.route("/tickets", methods=["GET"])
def get_tickets():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        page = max(request.args.get("page", 1, type=int), 1)
        limit = request.args.get("limit", 20, type=int)
        limit = min(max(limit, 1), 100)

        dataset_id = request.args.get("dataset_id", type=int)
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        status = request.args.get("status", "").strip()
        priority = request.args.get("priority", "").strip()
        confidence = request.args.get("confidence", "").strip()

        conditions = []
        params = []

        if dataset_id is not None:
            conditions.append("dataset_id = ?")
            params.append(dataset_id)

        if search:
            conditions.append("""
                (
                    ticket_id LIKE ?
                    OR ticket_summary LIKE ?
                    OR documented_issue LIKE ?
                )
            """)
            search_value = f"%{search}%"
            params.extend([search_value, search_value, search_value])

        if category:
            conditions.append("problem_category = ?")
            params.append(category)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if priority:
            conditions.append("priority = ?")
            params.append(priority)

        if confidence:
            conditions.append("confidence = ?")
            params.append(confidence)

        where_clause = ""

        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        cursor.execute(
            f"SELECT COUNT(*) FROM tickets {where_clause}",
            params
        )

        total_tickets = cursor.fetchone()[0]

        offset = (page - 1) * limit

        cursor.execute(f"""
            SELECT
                id,
                dataset_id,
                ticket_id,
                ticket_summary,
                problem_category,
                status,
                priority,
                age_days,
                recommended_action,
                possible_solution,
                actual_resolution,
                confidence
            FROM tickets
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        tickets = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            "success": True,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_tickets": total_tickets,
                "total_pages": (total_tickets + limit - 1) // limit
            },
            "filters": {
                "dataset_id": dataset_id,
                "search": search,
                "category": category,
                "status": status,
                "priority": priority,
                "confidence": confidence
            },
            "tickets": tickets
        })

    finally:
        connection.close()


# --------------------------------------------------
# GET ONE TICKET'S FULL ANALYSIS
# URL: GET /api/tickets/<ticket_row_id>
# --------------------------------------------------

@ticket_bp.route("/tickets/<int:ticket_row_id>", methods=["GET"])
def get_ticket_detail(ticket_row_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM tickets
            WHERE id = ?
        """, (ticket_row_id,))

        row = cursor.fetchone()

        if row is None:
            return jsonify({
                "success": False,
                "message": "Ticket not found"
            }), 404

        ticket = dict(row)

        if ticket.get("full_analysis"):
            try:
                ticket["full_analysis"] = json.loads(
                    ticket["full_analysis"]
                )
            except (json.JSONDecodeError, TypeError):
                pass

        return jsonify({
            "success": True,
            "ticket": ticket
        })

    finally:
        connection.close()

    
# --------------------------------------------------
# GET FULL DATASET ANALYTICS
# URL: GET /api/datasets/<dataset_id>/summary
# --------------------------------------------------

@ticket_bp.route("/datasets/<int:dataset_id>/summary", methods=["GET"])
def get_dataset_summary(dataset_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check whether the dataset exists.
        cursor.execute("""
            SELECT id, dataset_name, original_filename, total_tickets
            FROM datasets
            WHERE id = ?
        """, (dataset_id,))

        dataset = cursor.fetchone()

        if dataset is None:
            return jsonify({
                "success": False,
                "message": "Dataset not found"
            }), 404

        # Retrieve every ticket, not just the current frontend page.
        cursor.execute("""
            SELECT
                problem_category,
                status,
                priority,
                age_days
            FROM tickets
            WHERE dataset_id = ?
        """, (dataset_id,))

        rows = cursor.fetchall()

        total = len(rows)

        def make_distribution(counts, field_name):
            result = []

            for name, count in sorted(
                counts.items(),
                key=lambda item: item[1],
                reverse=True
            ):
                result.append({
                    field_name: name,
                    "ticket_count": count,
                    "percentage": round(
                        (count / total) * 100, 2
                    ) if total else 0
                })

            return result

        category_counts = {}
        status_counts = {}
        priority_counts = {}

        aging_counts = {
            "0-6 days": 0,
            "7-14 days": 0,
            "15-29 days": 0,
            "30-59 days": 0,
            "60+ days": 0,
            "Unknown": 0
        }

        for row in rows:
            # Category
            category = row["problem_category"] or "Unclassified"
            category_counts[category] = (
                category_counts.get(category, 0) + 1
            )

            # Status
            status = row["status"] or "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

            # Priority
            priority = row["priority"] or "Unknown"
            priority_counts[priority] = (
                priority_counts.get(priority, 0) + 1
            )

            # Aging
            age = row["age_days"]

            if age is None:
                aging_counts["Unknown"] += 1
            elif age < 7:
                aging_counts["0-6 days"] += 1
            elif age < 15:
                aging_counts["7-14 days"] += 1
            elif age < 30:
                aging_counts["15-29 days"] += 1
            elif age < 60:
                aging_counts["30-59 days"] += 1
            else:
                aging_counts["60+ days"] += 1

        # Keep aging bands in logical order.
        aging_distribution = [
            {
                "aging_band": band,
                "ticket_count": count,
                "percentage": round(
                    (count / total) * 100, 2
                ) if total else 0
            }
            for band, count in aging_counts.items()
            if count > 0
        ]

        return jsonify({
            "success": True,
            "dataset": dict(dataset),
            "summary": {
                "total_tickets": total,
                "category_distribution": make_distribution(
                    category_counts, "problem_category"
                ),
                "status_distribution": make_distribution(
                    status_counts, "status"
                ),
                "priority_distribution": make_distribution(
                    priority_counts, "priority"
                ),
                "aging_distribution": aging_distribution,
                "team_distribution": [],
                "team_data_available": False
            }
        })

    finally:
        connection.close()
