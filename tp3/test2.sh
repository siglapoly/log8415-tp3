std_ip=$(python3 start_standalone_sql.py) #"$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" "$AWS_DEFAULT_REGION"

#start standalone sysbench from local and save output in standalone_sysbench.log
ssh -i bot.pem ubuntu@"$std_ip" "sudo sysbench --db-driver=mysql --mysql-user=root --mysql-db=sakila --table-size=10000 /usr/share/sysbench/oltp_read_only.lua run" > standalone_sysbench_output.log
