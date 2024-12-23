#version 330

in vec3 in_vert;
in vec3 in_norm;

uniform mat4 mat_M;
uniform mat4 mat_V;
uniform mat4 mat_P;
uniform mat4 mat_MV;
uniform mat4 mat_MVP;

out vec4 vert_pos_view;
out vec4 vert_norm_world;
out vec4 vert_norm_view;

void main() {
  vert_pos_view = mat_MV * vec4(in_vert, 1);
  vert_norm_world = mat_M * vec4(in_norm, 0);
  vert_norm_view = mat_MV * vec4(in_norm, 0);
  gl_Position = mat_MVP * vec4(in_vert, 1);
}
