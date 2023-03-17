#!/usr/bin/python3
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2022. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN 'AS IS' BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# ******************************************************************************/
"""
Time:
Author:
Description: Manager that start aops-zeus
"""
from flask import g
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import scoped_session
import redis
from redis import RedisError
from vulcanus.database.table import User, Base, create_utils_tables
from vulcanus.log.log import LOGGER
from vulcanus.restful.resp.state import SUCCEED
from vulcanus.manage import init_app
from vulcanus.database.proxy import RedisProxy
from zeus.database import ENGINE
from zeus.database.proxy.account import UserProxy
from zeus.conf import configuration


def init_user():
    """
    Initialize user, add a default user: admin
    """
    try:
        create_utils_tables(Base, ENGINE)
    except sqlalchemy.exc.SQLAlchemyError:
        raise sqlalchemy.exc.SQLAlchemyError("create tables fail")

    proxy = UserProxy()
    if not proxy.connect(g.session):
        raise ValueError("connect to mysql fail")

    data = {
        "username": "admin",
        "password": "changeme"
    }
    res = proxy.select([User.username], {"username": data['username']})
    # user has been added to database, return
    if res[1]:
        return

    res = proxy.add_user(data)
    if res != SUCCEED:
        raise ValueError("add admin user fail")

    LOGGER.info("initialize default admin user succeed")


def init_database():
    """
    Initialize database
    """
    init_user()


def init_redis_connect():
    """
    Init redis connect
    """
    try:
        redis_connect = RedisProxy(configuration)
        redis_connect.connect()
    except (RedisError, redis.ConnectionError):
        raise RedisError("redis connect error.")


def main():

    app, config = init_app('zeus')

    @app.before_request
    def create_dbsession():
        g.session = scoped_session(sessionmaker(bind=ENGINE))

    @app.teardown_request
    def remove_dbsession(response):
        g.session.remove()
        return response

    @app.before_first_request
    def init_service():
        g.session = scoped_session(sessionmaker(bind=ENGINE))
        init_database()
        init_redis_connect()

    ip = config.get('IP')
    port = config.get('PORT')
    app.run(host=ip, port=port)


if __name__ == "__main__":
    main()
