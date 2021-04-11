import java.io.File;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;

import com.github.gumtreediff.client.Run;

public class AST_Parser{
    public static String[] getFileList(String dirName) {
        String[] fileList = {};
        File f1 = new File(dirName);
        if (f1.isDirectory()) {
            fileList = f1.list();
        }
        for (int i = 0; i < fileList.length; i++) {
            fileList[i] = dirName + "/" + fileList[i];
        }
        return fileList;
    }

    public static String[] getAllBugFileList(String dirName) {
        ArrayList<String> fList1 = new ArrayList<String>();
        ArrayList<String> fList2 = new ArrayList<String>(); 

        Collections.addAll(fList1, getFileList(dirName));

        for (String file1 : fList1) {
            Collections.addAll(fList2, getFileList(file1));
        }

        return fList2.toArray(new String[fList2.size()]);
    }

    public static void printList(String[] list) {
        for (int i=0; i<list.length; i++) {
            System.out.println(list[i].toString());
        }
    }

    public static String[] getBugFiles(String dirName) {
        return getFileList(dirName + "/buggy-version/");
    }

    public static void createDir(String destDirName) {
        File dir = new File(destDirName);
        if (!dir.exists()) {
            dir.mkdirs();
        }
    }

    public static void extractBugFix() {
        String[] fileList = getAllBugFileList("/home/zander/JIT-DP/BugFixDataset/");

        for (int i = 0; i < fileList.length; i++) {
            String[] bugFiles = getBugFiles(fileList[i]);
            for (String bugFile : bugFiles) {
                String[] splitBugFile = bugFile.replaceAll("//", "/").split("/");
                splitBugFile[splitBugFile.length-2] = "buggy-ast";
                String output = String.join("/", splitBugFile);
                splitBugFile[splitBugFile.length-1] = "";
                String outputDir = String.join("/", splitBugFile);
                createDir(outputDir);

                String[] origArgs = {"-f", "JSON", "-g", "java-jdt", "-o", output, bugFile};

                Run.initClients();

                Serializer client = new Serializer(origArgs);
                try {
                    client.run();
                } catch (Exception e) {
                    e.printStackTrace();
                }

            }
            if (i % 100 == 0) {
                String log = String.format("Cur: %d     Total: %d       Comp: %d", i, fileList.length, 100*i/fileList.length);
                System.out.println(log);
            }
        }
    }

    public static String[] getAllCommitFiles(String dirName) {
        ArrayList<String> pjList = new ArrayList<String>();
        ArrayList<String> cmList = new ArrayList<String>(); 

        Collections.addAll(pjList, getFileList(dirName));

        for (String project : pjList) {
            Collections.addAll(cmList, getFileList(project+"/code/"));
        }

        return cmList.toArray(new String[cmList.size()]);
    }

    public static String[] getCommitFiles(String dirName) {
        ArrayList<String> filesList = new ArrayList<String>();
        Collections.addAll(filesList, getFileList(dirName));

        Iterator<String> it = filesList.iterator();
        while (it.hasNext()) {
            String file = it.next();

            if (!file.endsWith(".java")) {
                it.remove();
            }
        }

        return filesList.toArray(new String[filesList.size()]);
    }

    public static void extractCommit() {
        String[] fileList = getAllCommitFiles("/home/zander/JIT-DP/Data_Extraction/git_base/datasets/");

        for (int i = 0; i < fileList.length; i++) {
            String[] commitFiles = getCommitFiles(fileList[i]);
            for (String commitFile : commitFiles) {
                String[] splitCommitFile = commitFile.replaceAll("//", "/").split("/");
                splitCommitFile[splitCommitFile.length-2] = splitCommitFile[splitCommitFile.length-2]+"/code-ast";
                String output = String.join("/", splitCommitFile);
                splitCommitFile[splitCommitFile.length-1] = "";
                String outputDir = String.join("/", splitCommitFile);
                createDir(outputDir);

                String[] origArgs = {"-f", "JSON", "-g", "java-jdt", "-o", output, commitFile};

                Run.initClients();

                Serializer client = new Serializer(origArgs);
                try {
                    client.run();
                } catch (Exception e) {
                    e.printStackTrace();
                }

            }
            if (i % 100 == 0) {
                String log = String.format("Cur: %d     Total: %d       Comp: %d", i, fileList.length, 100*i/fileList.length);
                System.out.println(log);
            }
        }
    }

    public static void main(String[] args) {
        // extractBugFix();
        extractCommit();
    }
}