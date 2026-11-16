// PortDump for Logisim-evolution (library classes were renamed): prints every port location,
// relative to the component's loc, for given attribute values.
// Build: javac -cp evolution-3.8.0/logisim-evolution-3.8.0-all.jar PortDumpEvo.java   (JDK 17)
// Run:   java -cp "evolution-3.8.0/logisim-evolution-3.8.0-all.jar;." PortDumpEvo "Memory|ROM|addrWidth=4;dataWidth=8"
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.comp.ComponentFactory;
import com.cburch.logisim.comp.EndData;
import com.cburch.logisim.data.Attribute;
import com.cburch.logisim.data.AttributeSet;
import com.cburch.logisim.data.Location;
import com.cburch.logisim.tools.AddTool;
import com.cburch.logisim.tools.Library;
import com.cburch.logisim.tools.Tool;

public class PortDumpEvo {
    static Library lib(String name) {
        if (name.equals("Wiring")) return new com.cburch.logisim.std.wiring.WiringLibrary();
        if (name.equals("Gates")) return new com.cburch.logisim.std.gates.GatesLibrary();
        if (name.equals("Plexers")) return new com.cburch.logisim.std.plexers.PlexersLibrary();
        if (name.equals("Arithmetic")) return new com.cburch.logisim.std.arith.ArithmeticLibrary();
        if (name.equals("Memory")) return new com.cburch.logisim.std.memory.MemoryLibrary();
        if (name.equals("I/O")) return new com.cburch.logisim.std.io.IoLibrary();
        throw new IllegalArgumentException(name);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void main(String[] args) {
        for (String spec : args) {
            String[] parts = spec.split("\\|", -1);
            ComponentFactory factory = null;
            for (Tool t : lib(parts[0]).getTools()) {
                if (t instanceof AddTool && ((AddTool) t).getFactory().getName().equals(parts[1])) {
                    factory = ((AddTool) t).getFactory();
                }
            }
            if (factory == null) throw new IllegalArgumentException("no factory " + parts[1]);
            AttributeSet attrs = (AttributeSet) factory.createAttributeSet().clone();
            if (parts.length > 2 && !parts[2].isEmpty()) {
                for (String kv : parts[2].split(";")) {
                    String[] p = kv.split("=", 2);
                    Attribute a = attrs.getAttribute(p[0]);
                    if (a == null) throw new IllegalArgumentException("no attr " + p[0] + " on " + parts[1]);
                    attrs.setValue(a, a.parse(p[1]));
                }
            }
            Component c = factory.createComponent(Location.create(0, 0, true), attrs);
            System.out.println("== " + spec + "  bounds=" + c.getBounds());
            int i = 0;
            for (EndData e : c.getEnds()) {
                Location l = e.getLocation();
                String io = e.isInput() && e.isOutput() ? "io" : e.isInput() ? "in" : "out";
                System.out.println("  [" + i++ + "] (" + l.getX() + "," + l.getY() + ") w=" + e.getWidth().getWidth() + " " + io);
            }
        }
    }
}
