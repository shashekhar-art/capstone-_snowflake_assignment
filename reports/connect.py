import snowflake.connector

def get_conn():
    return snowflake.connector.connect(
        account   = "uq57089.ap-southeast-7.aws",
        user      = "shashekhar",
        password  = "Sha@rock@54321",
        warehouse = "COMPUTE_WH",
        database  = "ADVENTURE_WORKS_DB",
        schema    = "GOLD"
    )
