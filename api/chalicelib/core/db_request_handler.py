import logging
from chalicelib.utils import helper, pg_client
# DatabaseRequestHandler 类是一个通用的数据库请求处理工具类，用于构建和执行数据库查询操作。
# 它可以处理增、删、改、查操作，支持复杂的查询构建，包括连接、子查询、排序、分组、分页等。这个类提供了一个灵活的接口来与 PostgreSQL 数据库进行交互。
# DatabaseRequestHandler 类提供了一种灵活且可扩展的方式来构建和执行 SQL 查询。这种设计适用于需要处理复杂数据库操作的应用程序，特别是在动态生成查询、支持复杂的约束和子查询方面非常有用。
# 主要功能包括：
# 动态生成 SQL 查询（支持 SELECT、INSERT、UPDATE、DELETE 操作）。
# 支持复杂的 JOIN、GROUP BY、ORDER BY、LIMIT 和 OFFSET 子句。
# 提供批量插入和更新的支持。
# 提供原始 SQL 查询执行接口。
# 使用了 mogrify 方法来确保 SQL 查询的安全性和正确性。
# 这些功能使得 DatabaseRequestHandler 类在处理复杂数据库操作时非常实用，同时保持了代码的简洁性和可维护性。

class DatabaseRequestHandler:
    """
    初始化数据库请求处理器实例。
    :param table_name: 要操作的数据库表名称。
    """
    def __init__(self, table_name):
        self.table_name = table_name
        self.constraints = []  # 用于存储查询约束条件的列表
        self.params = {}  # 用于存储查询参数的字典
        self.order_clause = "" # 存储ORDER BY子句
        self.sort_clause = "" # 存储排序方向
        self.select_columns = [] # 存储SELECT子句中的列名
        self.sub_queries = [] # 存储子查询和别名
        self.joins = []  # 存储JOIN子句
        self.group_by_clause = "" # 存储GROUP BY子句
        self.client = pg_client  # 数据库客户端
        self.logger = logging.getLogger(__name__) # 日志记录器
        self.pagination = {} # 存储分页信息


    def add_constraint(self, constraint, param=None):
        """
        添加查询约束条件。
        :param constraint: SQL WHERE 子句中的条件。
        :param param: 与条件相关的参数字典。
        """
        self.constraints.append(constraint)
        if param:
            self.params.update(param)

    def add_subquery(self, subquery, alias, param=None):
        """
        添加子查询。
        :param subquery: SQL 子查询语句。
        :param alias: 子查询的别名。
        :param param: 与子查询相关的参数字典。
        """
        self.sub_queries.append((subquery, alias))
        if param:
            self.params.update(param)

    def add_join(self, join_clause):
        """
        添加JOIN子句。
        :param join_clause: SQL JOIN 语句。
        """
        self.joins.append(join_clause)

    def add_param(self, key, value):
        """
        添加或更新查询参数。
        :param key: 参数名。
        :param value: 参数值。
        """
        self.params[key] = value

    def set_order_by(self, order_by):
        """
        设置ORDER BY子句。
        :param order_by: SQL ORDER BY 语句。
        """
        self.order_clause = order_by

    def set_sort_by(self, sort_by):
        """
        设置排序方向。
        :param sort_by: 排序方向（如ASC或DESC）。
        """
        self.sort_clause = sort_by

    def set_select_columns(self, columns):
        """
        设置SELECT子句中的列。
        :param columns: 列名列表。
        """
        self.select_columns = columns

    def set_group_by(self, group_by_clause):
        """
        设置GROUP BY子句。
        :param group_by_clause: SQL GROUP BY 语句。
        """
        self.group_by_clause = group_by_clause

    def set_pagination(self, page, page_size):
        """
        设置分页参数。
        :param page: 页码（从1开始）。
        :param page_size: 每页的条目数。
        """
        """
        Set pagination parameters for the query.
        :param page: The page number (1-indexed)
        :param page_size: Number of items per page
        """
        self.pagination = {
            'offset': (page - 1) * page_size,
            'limit': page_size
        }

    def build_query(self, action="select", additional_clauses=None, data=None):
        """
        构建SQL查询语句。
        :param action: 查询类型（select, insert, update, delete）。
        :param additional_clauses: 额外的SQL子句。
        :param data: 用于插入或更新的数据字典。
        :return: 完整的SQL查询字符串。
        """
        if action == "select":
            query = f"SELECT {', '.join(self.select_columns)} FROM {self.table_name}"
        elif action == "insert":
            columns = ', '.join(data.keys())
            placeholders = ', '.join(f'%({k})s' for k in data.keys())
            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        elif action == "update":
            set_clause = ', '.join(f"{k} = %({k})s" for k in data.keys())
            query = f"UPDATE {self.table_name} SET {set_clause}"
        elif action == "delete":
            query = f"DELETE FROM {self.table_name}"

        for join in self.joins:
            query += f" {join}"
        for subquery, alias in self.sub_queries:
            query += f", ({subquery}) AS {alias}"
        if self.constraints:
            query += " WHERE " + " AND ".join(self.constraints)
        if action == "select":
            if self.group_by_clause:
                query += " GROUP BY " + self.group_by_clause
            if self.sort_clause:
                query += " ORDER BY " + self.sort_clause
            if self.order_clause:
                query += " " + self.order_clause
            if hasattr(self, 'pagination') and self.pagination:
                query += " LIMIT %(limit)s OFFSET %(offset)s"
                self.params.update(self.pagination)

        if additional_clauses:
            query += " " + additional_clauses

        logging.debug(f"Query: {query}")
        return query

    def execute_query(self, query, data=None):
        """
        执行SQL查询。
        :param query: SQL查询字符串。
        :param data: 传递给查询的额外数据。
        :return: 查询结果。
        """
        try:
            with self.client.PostgresClient() as cur:
                mogrified_query = cur.mogrify(query, {**data, **self.params} if data else self.params)
                cur.execute(mogrified_query)
                return cur.fetchall() if cur.description else None
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            raise

    def fetchall(self):
        """
        执行SELECT查询并获取所有结果。
        :return: 查询结果列表。
        """
        query = self.build_query()
        return self.execute_query(query)

    def fetchone(self):
        """
        执行SELECT查询并获取单个结果。
        :return: 查询结果中的第一行。
        """
        query = self.build_query()
        result = self.execute_query(query)
        return result[0] if result else None

    def insert(self, data):
        """
        执行INSERT操作。
        :param data: 要插入的数据字典。
        :return: 插入后的记录。
        """
        query = self.build_query(action="insert", data=data)
        query += " RETURNING *;"

        result = self.execute_query(query, data)
        return result[0] if result else None

    def update(self, data):
        """
        执行UPDATE操作。
        :param data: 要更新的数据字典。
        :return: 更新后的记录。
        """
        query = self.build_query(action="update", data=data)
        query += " RETURNING *;"

        result = self.execute_query(query, data)
        return result[0] if result else None

    def delete(self):
        """
        执行DELETE操作。
        :return: 删除操作的结果。
        """
        query = self.build_query(action="delete")
        return self.execute_query(query)

    def batch_insert(self, items):
        """
        批量插入操作。
        :param items: 要插入的数据字典列表。
        :return: 插入后的记录列表。
        """
        if not items:
            return None

        columns = ', '.join(items[0].keys())

        # Building a values string with unique parameter names for each item
        all_values_query = ', '.join(
            '(' + ', '.join([f"%({key}_{i})s" for key in item]) + ')'
            for i, item in enumerate(items)
        )

        query = f"INSERT INTO {self.table_name} ({columns}) VALUES {all_values_query} RETURNING *;"

        try:
            with self.client.PostgresClient() as cur:
                # Flatten items into a single dictionary with unique keys
                combined_params = {f"{k}_{i}": v for i, item in enumerate(items) for k, v in item.items()}
                mogrified_query = cur.mogrify(query, combined_params)
                cur.execute(mogrified_query)
                return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Database batch insert operation failed: {e}")
            raise

    def raw_query(self, query, params=None):
        """
        执行原始SQL查询。
        :param query: SQL查询字符串。
        :param params: 查询参数字典。
        :return: 查询结果。
        """
        try:
            with self.client.PostgresClient() as cur:
                mogrified_query = cur.mogrify(query, params)
                cur.execute(mogrified_query)
                return cur.fetchall() if cur.description else None
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            raise

    def batch_update(self, items):
        """
        批量更新操作。
        :param items: 要更新的数据字典列表。
        :return: 更新操作的结果。
        """
        if not items:
            return None

        id_column = list(items[0])[0]

        # Building the set clause for the update statement
        update_columns = list(items[0].keys())
        update_columns.remove(id_column)
        set_clause = ', '.join([f"{col} = v.{col}" for col in update_columns])

        # Building the values part for the 'VALUES' section
        values_rows = []
        for item in items:
            values = ', '.join([f"%({key})s" for key in item.keys()])
            values_rows.append(f"({values})")
        values_query = ', '.join(values_rows)

        # Constructing the full update query
        query = f"""
            UPDATE {self.table_name} AS t 
            SET {set_clause} 
            FROM (VALUES {values_query}) AS v ({', '.join(items[0].keys())}) 
            WHERE t.{id_column} = v.{id_column};
        """

        try:
            with self.client.PostgresClient() as cur:
                # Flatten items into a single dictionary for mogrify
                combined_params = {k: v for item in items for k, v in item.items()}
                mogrified_query = cur.mogrify(query, combined_params)
                cur.execute(mogrified_query)
        except Exception as e:
            self.logger.error(f"Database batch update operation failed: {e}")
            raise
