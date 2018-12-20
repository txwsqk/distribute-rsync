# 概述

通过 redis 队列实现分布式 rsync

以2的指数形态并发 rsync 同步文件

C/S 结构

# 说明

```bash
task = 'task'  要同步文件的绝对路径
lookup = 'lookup' 发现任务 lookup +1
synchronize_queue = 'synchronize_queue'  set类型,同步完成的机器会把ip存入供其他rsync使用
finished_queue = 'finished_queue'        同上,记录完成任务的机器ip
running_queue = 'running_queue'          set类型,正在执行任务的机器ip
```

# 使用

1. pip install redis
2. 所有要同步的机器上配置 rsync daemon

```bash
[repo]
uid = linkedme
gid = linkedme
path = /data1/repo
read only = no
auth users = sre
secrets file = /etc/rsyncd.secrets
```

2.  master 和 minion 脚本以 cron 方式运行

   * minion

   ```bash
   */2 * * * * /root/.env/bin/python /data1/scripts/sync_file_minion.py >> /var/log/sync_file_minion.log
   ```

   * master

   ```bash
   */2 * * * * /root/.env/bin/python /data1/scripts/sync_file_master.py >> /var/log/sync_file_master.log 2>&1
   ```

# 实际使用

同步一个1.7G 的文件到195台机器

手动触发一个任务

```bash
192.168.254.11:6379[10]> set task /data1/rsync_data/ctr_model/model.20181220011501
OK
```

观察日志

* master

```bash
20-Dec-18 17:16:01 - no task, exit
20-Dec-18 17:18:01 - try to find a task
20-Dec-18 17:18:01 - no task, exit
20-Dec-18 17:20:01 - try to find a task
20-Dec-18 17:20:01 - file_name: /data1/rsync_data/ctr_model/model.20181220011501, finished_minion_count: 0
20-Dec-18 17:20:01 - found new task, start rsync and set redis queue
20-Dec-18 17:20:01 - rsync complete:
sending incremental file list

sent 86 bytes  received 12 bytes  196.00 bytes/sec
total size is 1,747,109,690  speedup is 17,827,649.90


start rsync to minion: /data1/rsync_data/ctr_model/model.20181220011501
20-Dec-18 17:22:01 - try to find a task
20-Dec-18 17:22:01 - file_name: /data1/rsync_data/ctr_model/model.20181220011501, finished_minion_count: 194
20-Dec-18 17:22:01 - nothing to do
20-Dec-18 17:24:02 - try to find a task
20-Dec-18 17:24:02 - file_name: /data1/rsync_data/ctr_model/model.20181220011501, finished_minion_count: 195
20-Dec-18 17:24:02 - mission complete, clean task and queue
20-Dec-18 17:26:01 - try to find a task
20-Dec-18 17:26:01 - no task, exit
20-Dec-18 17:28:01 - try to find a task
20-Dec-18 17:28:01 - no task, exit
20-Dec-18 17:30:01 - try to find a task
```

耗时 4分钟

* minion

```bash
20-Dec-18 17:21:10 - try to get a avaiable rsync source
20-Dec-18 17:21:10 - try to get a avaiable rsync source
20-Dec-18 17:21:19 - try to get a avaiable rsync source
20-Dec-18 17:21:19 - add lock to running_queue
20-Dec-18 17:21:19 - start rsync from 192.168.254.27
20-Dec-18 17:21:19 - START rsync:
  syn_queue:0
  fin_queue:72

20-Dec-18 17:21:31 - rsync complete:
receiving incremental file list
./
model.20181220011501

sent 46 bytes  received 1,747,536,349 bytes  139,802,911.60 bytes/sec
total size is 1,747,109,690  speedup is 1.00


20-Dec-18 17:21:31 - END rsync:
  syn_queue:113
  fin_queue:154
```

每秒 139M



# 结论

之前使用 salt 同步, 每秒只有6M, 同步完195台机器需要 N 个小时, 因为我们只有一个 rsync 源, 并发也不能开太高.

666
