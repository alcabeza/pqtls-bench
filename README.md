# PQ-TLS demo on Amazon S3 (hybrid ECDH + ML-KEM TLS)

A disposable environment to check that Amazon S3 negotiates hybrid post-quantum TLS
and to measure its impact on latency. Source: the AWS documentation page
"Configuring hybrid post-quantum TLS for your client".

## Contents
- `pqtls-demo-stack.yaml`: CloudFormation template (private S3 bucket, EC2 instance with no inbound port reachable through SSM, OpenSSL 3.5, Java 17, Maven, embedded benchmark scripts)
- `pq_handshake_bench.py`: handshake benchmark, X25519 vs X25519MLKEM768 (already embedded in the instance)
- `java/`: application-level Java benchmark (AWS SDK + CRT client, cold/warm, with and without PQ-TLS), already embedded in the instance

The scripts are provided here for reading and reuse; **the template alone is enough** to deploy everything.

## Deployment
Prerequisites: an AWS account and a region (e.g. eu-west-3).

    aws cloudformation deploy --template-file pqtls-demo-stack.yaml \
      --stack-name pqtls-demo --capabilities CAPABILITY_IAM --region eu-west-3

(or in the console: CloudFormation > Create stack > Upload a template, and tick the IAM acknowledgement at the end).

## Usage
1. Wait 10 to 15 minutes after `CREATE_COMPLETE` (OpenSSL build, Maven warm-up).
2. EC2 > instance `pqtls-demo` > Connect > Session Manager.
3. Check: `ls /opt/pqdemo/READY` (log: `/var/log/pqdemo-setup.log`).
4. Run:

       pq-demo            # classic vs hybrid handshake + S3 round trip
       pq-bench --runs 30 # handshake benchmark (median, p95)
       pq-java-bench 30   # Java benchmark, cold/warm, with and without PQ-TLS
       sudo pq-capture    # network capture (Wireshark: tls.handshake.type == 1)

The group `X25519MLKEM768` should appear as negotiated in the second block of `pq-demo`.

## Cleanup (important)
    aws s3 rm s3://<BucketName> --recursive
    aws cloudformation delete-stack --stack-name pqtls-demo --region eu-west-3

## Limitations
- Deployment and demo validated on a real AWS account (eu-west-3). In case of error, check `/var/log/pqdemo-setup.log`.
- The duration measured by `pq-bench` includes openssl process startup: only the gap between modes is meaningful.
- The Java benchmark runs the classic mode first, so JVM and client warm-up can bias the comparison in favor of the second mode. Do not draw conclusions about PQ-TLS overhead from it alone; rely on `pq-bench` for the handshake.
- Since Java SDK 2.35.11, PQ-TLS is enabled by default; the benchmark forces `false` for the classic baseline.
- Resources are billed as long as the stack exists.
