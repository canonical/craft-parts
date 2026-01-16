  package org.starcraft;

  import org.gradle.api.Plugin;
  import org.gradle.api.Project;

  public class HelloPlugin implements Plugin<Project> {
      @Override
      public void apply(Project project) {
          project.getExtensions().getExtraProperties().set("helloPluginApplied", true);
      }
  }

