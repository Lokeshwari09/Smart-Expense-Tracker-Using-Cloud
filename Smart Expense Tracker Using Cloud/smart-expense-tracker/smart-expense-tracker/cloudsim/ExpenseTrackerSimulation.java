package expense;

import org.cloudbus.cloudsim.*;
import org.cloudbus.cloudsim.core.CloudSim;
import org.cloudbus.cloudsim.provisioners.*;

import java.text.DecimalFormat;
import java.util.*;

/**
 * Smart Expense Tracker - CloudSim 3.0.3 simulation.
 * 1 datacenter, 2 hosts, 4 VMs (backend servers), 20 cloudlets (user requests:
 * add expense, monthly summary, CSV export, S3 backup).
 *
 * Setup: add cloudsim-3.0.3.jar (+ commons-math3-3.x.jar) to the Java build path
 * in VS Code ("Extension Pack for Java"), then run this class.
 */
public class ExpenseTrackerSimulation {

    public static void main(String[] args) throws Exception {
        CloudSim.init(1, Calendar.getInstance(), false);

        Datacenter dc = createDatacenter("ExpenseTracker-DC");
        DatacenterBroker broker = new DatacenterBroker("ExpenseBroker");

        List<Vm> vms = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            vms.add(new Vm(i, broker.getId(), 1000, 1, 1024, 1000, 10000, "Xen",
                    new CloudletSchedulerTimeShared()));
        }
        broker.submitVmList(vms);

        List<Cloudlet> cloudlets = new ArrayList<>();
        Random rnd = new Random(42);
        UtilizationModel full = new UtilizationModelFull();
        for (int i = 0; i < 20; i++) {
            long length = 20000 + rnd.nextInt(60000);
            Cloudlet c = new Cloudlet(i, length, 1, 300, 300, full, full, full);
            c.setUserId(broker.getId());
            cloudlets.add(c);
        }
        broker.submitCloudletList(cloudlets);

        CloudSim.startSimulation();
        List<Cloudlet> done = broker.getCloudletReceivedList();
        CloudSim.stopSimulation();

        print(done);
    }

    private static Datacenter createDatacenter(String name) throws Exception {
        List<Host> hosts = new ArrayList<>();
        for (int h = 0; h < 2; h++) {
            List<Pe> pes = new ArrayList<>();
            for (int p = 0; p < 4; p++) pes.add(new Pe(p, new PeProvisionerSimple(1000)));
            hosts.add(new Host(h, new RamProvisionerSimple(8192), new BwProvisionerSimple(100000),
                    1000000, pes, new VmSchedulerTimeShared(pes)));
        }
        DatacenterCharacteristics ch = new DatacenterCharacteristics("x86", "Linux", "Xen", hosts,
                5.5, 3.0, 0.05, 0.001, 0.0);
        return new Datacenter(name, ch, new VmAllocationPolicySimple(hosts), new LinkedList<Storage>(), 0);
    }

    private static void print(List<Cloudlet> list) {
        DecimalFormat f = new DecimalFormat("###.##");
        System.out.println("\n========== SIMULATION OUTPUT ==========");
        System.out.println("Request  Status   VM   Start    Finish   Time");
        double total = 0;
        for (Cloudlet c : list) {
            if (c.getStatus() == Cloudlet.SUCCESS) {
                System.out.println("   " + c.getCloudletId() + "     SUCCESS   " + c.getVmId() + "   "
                        + f.format(c.getExecStartTime()) + "     " + f.format(c.getFinishTime())
                        + "     " + f.format(c.getActualCPUTime()));
                total += c.getActualCPUTime();
            }
        }
        System.out.println("Average execution time: " + f.format(total / list.size()) + " s");
    }
}
