aws configure --profile Solo
aws codebuild list-projects --profile Solo
aws codebuild batch-get-projects --names <project> --profile Solo
aws configure --profile Calrissian
aws rds describe-db-instances --profile Calrissian
aws rds create-db-snapshot --db-instance-identifier <instanceID> --db-snapshot-identifier cloudgoat --profile Calrissian
aws rds describe-db-subnet-groups --profile Calrissian
aws ec2 describe-security-groups --profile Calrissian
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier <DbInstanceID> --db-snapshot-identifier <scapshotId> --db-subnet-group-name <db subnet group> --publicly-accessible --vpc-security-group-ids <ec2-securitygroup> --profile Calrissian
aws rds modify-db-instance --db-instance-identifier <DbName> --master-user-password cloudgoat --profile Calrissian