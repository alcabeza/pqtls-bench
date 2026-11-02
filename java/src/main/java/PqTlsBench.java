import software.amazon.awssdk.http.async.SdkAsyncHttpClient;
import software.amazon.awssdk.http.crt.AwsCrtAsyncHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3AsyncClient;
import java.util.*;

/** Usage: PqTlsBench <bucket> [region] [runs]. Cold = new handshake for each measurement, warm = reused connection. */
public class PqTlsBench {
    public static void main(String[] args) {
        String bucket = args[0];
        Region region = Region.of(args.length > 1 ? args[1] : "eu-west-3");
        int runs = args.length > 2 ? Integer.parseInt(args[2]) : 30;
        for (boolean pq : new boolean[]{false, true}) {
            List<Double> cold = new ArrayList<>(), warm = new ArrayList<>();
            for (int i = 0; i < runs; i++) {
                try (SdkAsyncHttpClient h = http(pq); S3AsyncClient s3 = client(h, region)) {
                    long t0 = System.nanoTime();
                    s3.headBucket(b -> b.bucket(bucket)).join();
                    cold.add((System.nanoTime() - t0) / 1e6);
                }
            }
            try (SdkAsyncHttpClient h = http(pq); S3AsyncClient s3 = client(h, region)) {
                s3.headBucket(b -> b.bucket(bucket)).join();
                for (int i = 0; i < runs; i++) {
                    long t0 = System.nanoTime();
                    s3.headBucket(b -> b.bucket(bucket)).join();
                    warm.add((System.nanoTime() - t0) / 1e6);
                }
            }
            System.out.printf("%-22s cold: med %6.1f ms p95 %6.1f ms | warm: med %6.1f ms p95 %6.1f ms%n",
                pq ? "PQ-TLS (ECDH+ML-KEM)" : "Classic TLS", p(cold, 50), p(cold, 95), p(warm, 50), p(warm, 95));
        }
    }
    // Since SDK 2.35.11 PQ-TLS is on by default: we force false to get a classic baseline.
    static SdkAsyncHttpClient http(boolean pq) { return AwsCrtAsyncHttpClient.builder().postQuantumTlsEnabled(pq).build(); }
    static S3AsyncClient client(SdkAsyncHttpClient h, Region r) { return S3AsyncClient.builder().region(r).httpClient(h).build(); }
    static double p(List<Double> v, int pc) { List<Double> s = new ArrayList<>(v); Collections.sort(s); return s.get(Math.min(s.size() - 1, (int) Math.round(pc / 100.0 * (s.size() - 1)))); }
}
