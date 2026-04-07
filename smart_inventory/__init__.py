import pymysql

# Compatibility shim for Django MySQL backend version check when using PyMySQL.
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.__version__ = "2.2.1"

pymysql.install_as_MySQLdb()